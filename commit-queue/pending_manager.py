# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Commit queue manager class.

Security implications:

The following hypothesis are made:
- Commit queue:
  - Impersonate the same svn credentials that the patchset owner.
  - Can't impersonate a non committer.
  - SVN will check the committer write access.
"""

import logging
import os
import time
import traceback
import urllib2

import find_depot_tools  # pylint: disable=W0611
import checkout
import patch
import subprocess2

import errors
import model
from verification import base


class PendingCommit(base.Verified):
  """Represents a pending commit that is being processed."""
  # Important since they tell if we need to revalidate and send try jobs
  # again or not if any of these value changes.
  issue = int
  patchset = int
  description = unicode
  files = list
  # Only a cache, these values can be regenerated.
  owner = unicode
  reviewers = list
  base_url = unicode
  messages = list
  relpath = unicode
  # Only used after a patch was committed. Keeping here for try job retries.
  revision = (None, int, unicode)

  def __init__(self, **kwargs):
    super(PendingCommit, self).__init__(**kwargs)
    for message in self.messages:
      # Save storage, no verifier really need 'text', just 'approval'.
      if 'text' in message:
        del message['text']

  def pending_name(self):
    """The name that should be used for try jobs.

    It makes it possible to regenerate the try_jobs array if ever needed."""
    return '%d-%d' % (self.issue, self.patchset)

  def prepare_for_patch(self, context_obj):
    self.revision = context_obj.checkout.prepare(self.revision)
    # Verify revision consistency.
    if not self.revision:
      raise base.DiscardPending(
          self, 'Internal error: failed to checkout. Please try again.')

  def apply_patch(self, context_obj, prepare):
    """Applies the pending patch to the checkout and throws if it fails."""
    try:
      if prepare:
        self.prepare_for_patch(context_obj)
      patches = context_obj.rietveld.get_patch(self.issue, self.patchset)
      if not patches:
        raise base.DiscardPending(
            self, 'No diff was found for this patchset.')
      if self.relpath:
        patches.set_relpath(self.relpath)
      self.files = [p.filename for p in patches]
      if not self.files:
        raise base.DiscardPending(
            self, 'No file was found in this patchset.')
      context_obj.checkout.apply_patch(patches)
    except (checkout.PatchApplicationFailed, patch.UnsupportedPatchFormat), e:
      raise base.DiscardPending(self, str(e))
    except subprocess2.CalledProcessError, e:
      out = 'Failed to apply the patch.'
      if e.stdout:
        out += '\n%s' % e.stdout
      raise base.DiscardPending(self, out)
    except urllib2.HTTPError, e:
      raise base.DiscardPending(
          self,
          ('Failed to request the patch to try. Please note that binary files'
          'are still unsupported at the moment, this is being worked on.\n\n'
          'Thanks for your patience.\n\n%s') % e)


class PendingQueue(model.PersistentMixIn):
  """Represents the queue of pending commits being processed."""
  pending_commits = list


class PendingManager(object):
  """Fetch new issues from rietveld, pass the issues through all of verifiers
  and then commit the patches with checkout.
  """
  FAILED_NO_MESSAGE = (
      'Commit queue patch verification failed without an error message.\n'
      'Something went wrong, probably a crash, a hickup or simply\n'
      'the monkeys went out for dinner.\n'
      'Please email commit-bot@chromium.org with the CL url.')
  INTERNAL_EXCEPTION = (
      'Commit queue had an internal error.\n'
      'Something went really wrong, probably a crash, a hickup or\n'
      'simply the monkeys went out for dinner.\n'
      'Please email commit-bot@chromium.org with the CL url.')
  DESCRIPTION_UPDATED = (
      'Commit queue rejected this change because the description was changed\n'
      'between the time the change entered the commit queue and the time it\n'
      'was ready to commit. You can safely check the commit box again.')
  TRYING_PATCH = 'CQ is trying da patch. Follow status at\n'
  # Maximum number of commits done in a burst.
  MAX_COMMIT_BURST = 4
  # Delay (secs) between commit bursts.
  COMMIT_BURST_DELAY = 10*60

  def __init__(self, context_obj, pre_patch_verifiers, verifiers):
    """
    Args:
      pre_patch_verifiers: Verifiers objects that are run before applying the
                           patch.
      verifiers: Verifiers object run after applying the patch.
    """
    assert len(pre_patch_verifiers) or len(verifiers)
    self.context = context_obj
    self.pre_patch_verifiers = pre_patch_verifiers or []
    self.verifiers = verifiers or []
    self.all_verifiers = pre_patch_verifiers + verifiers
    self.queue = PendingQueue()
    # Keep the timestamps of the last few commits so that we can control the
    # pace (burstiness) of commits.
    self.recent_commit_timestamps = []
    # Assert names are unique.
    names = [x.name for x in pre_patch_verifiers + verifiers]
    assert len(names) == len(set(names))
    for verifier in self.pre_patch_verifiers:
      assert not isinstance(verifier, base.VerifierCheckout)

  def look_for_new_pending_commit(self):
    """Looks for new reviews on self.context.rietveld with c+ set.

    Calls _new_pending_commit() on all new review found.
    """
    try:
      new_issues = self._fetch_pending_issues()

      # If there is an issue in processed_issues that is not in new_issues,
      # discard it.
      for pending in self.queue.pending_commits:
        if not pending.issue in new_issues:
          logging.info('Flushing issue %d' % pending.issue)
          self.context.status.send(
              pending,
              { 'verification': 'abort',
                'payload': {
                  'output': 'CQ bit was unchecked on CL. Ignoring.' }})
          pending.get_state = lambda: base.IGNORED
          self._discard_pending(pending, None)

      # Find new issues.
      known_issues = [c.issue for c in self.queue.pending_commits]
      for issue_id in new_issues:
        if issue_id not in known_issues:
          issue_data = self.context.rietveld.get_issue_properties(
              issue_id, True)
          if issue_data['patchsets'] and issue_data['commit']:
            logging.info('Found new issue %d' % issue_data['issue'])
            self.queue.pending_commits.append(
                PendingCommit(
                    issue=issue_data['issue'],
                    owner=issue_data['owner_email'],
                    reviewers=issue_data['reviewers'],
                    patchset=issue_data['patchsets'][-1],
                    base_url=issue_data['base_url'],
                    description=issue_data['description'].replace('\r', ''),
                    messages=issue_data['messages']))
    except Exception, e:
      traceback.print_exc()
      # Swallow every exception in that code and move on. Make sure to send a
      # stack trace though.
      errors.send_stack(e)

  def _fetch_pending_issues(self):
    """Returns the list of issue number for reviews on Rietveld with their last
    patchset with commit+ flag set.
    """
    return self.context.rietveld.get_pending_issues()

  def process_new_pending_commit(self):
    """Starts verification on newly found pending commits."""
    expected = set(i.name for i in self.all_verifiers)
    for pending in self.queue.pending_commits[:]:
      try:
        # Take in account the case where a verifier was removed.
        done = set(pending.verifications.keys())
        missing = expected - done
        if (not missing or pending.get_state() != base.PROCESSING):
          continue
        logging.info(
            'Processing issue %s (%s, %d)' % (
                pending.issue, missing, pending.get_state()))
        self._verify_pending(pending)
      except base.DiscardPending, e:
        self._discard_pending(e.pending, e.status)
      except Exception, e:
        traceback.print_exc()
        # Swallow every exception in that code and move on. Make sure to send a
        # stack trace though.
        errors.send_stack(e)

  def update_status(self):
    """Updates the status for each pending commit verifier."""
    for verifier in self.all_verifiers:
      try:
        verifier.update_status(self.queue.pending_commits)
      except base.DiscardPending, e:
        # It's not efficient since it takes a full loop for each pending
        # commit to discard.
        self._discard_pending(e.pending, e.status)
      except Exception, e:
        traceback.print_exc()
        # Swallow every exception in that code and move on. Make sure to send
        # a stack trace though.
        errors.send_stack(e)

  def scan_results(self):
    """Scans pending commits that can be committed or discarded."""
    for pending in self.queue.pending_commits[:]:
      state = pending.get_state()
      if state == base.FAILED:
        self._discard_pending(
            pending, pending.error_message() or self.FAILED_NO_MESSAGE)
      elif state == base.SUCCEEDED:
        if self._throttle(pending):
          continue
        # The item is removed right away.
        self.queue.pending_commits.remove(pending)
        try:
          # Runs checks. It's be nice to run the test before the postpone,
          # especially if the tree is closed for a long moment but at the same
          # time it would keep fetching the rietveld status constantly.
          self._last_minute_checks(pending)
          self._commit_patch(pending)
        except base.DiscardPending, e:
          self._discard_pending(e.pending, e.status)
        except Exception, e:
          traceback.print_exc()
          errors.send_stack(e)
          self._discard_pending(pending, self.INTERNAL_EXCEPTION)
      else:
        # When state is IGNORED, we need to keep this issue so it's not fetched
        # another time but we can't discard it since we don't want to remove the
        # commit bit for another project hosted on the same code review
        # instance.
        assert state in (base.PROCESSING, base.IGNORED)

  def _verify_pending(self, pending):
    """Initiates all the verifiers on a pending change."""
    # Do not apply the patch if not necessary. It will be applied at commit
    # time anyway so if the patch doesn't apply, it'll be catch later.
    if not self._pending_run_verifiers(pending, self.pre_patch_verifiers):
      return

    if self.verifiers:
      pending.prepare_for_patch(self.context)

    # This CL is real business, alert the user that we're going to try his
    # patch.  Note that this is done *after* syncing but *before* applying the
    # patch.
    self.context.status.send(
        pending,
        { 'verification': 'initial',
          'payload': {'revision': pending.revision}})
    self.context.rietveld.add_comment(
        pending.issue,
        self.TRYING_PATCH + '%s/%s/%d/%d\n' % (
          self.context.status.url, pending.owner,
          pending.issue, pending.patchset))

    if self.verifiers:
      pending.apply_patch(self.context, False)
      previous_cwd = os.getcwd()
      try:
        os.chdir(self.context.checkout.project_path)
        self._pending_run_verifiers(pending, self.verifiers)
      finally:
        os.chdir(previous_cwd)

  @classmethod
  def _pending_run_verifiers(cls, pending, verifiers):
    """Runs verifiers on a pending change.

    Returns True if all Verifiers were run.
    """
    for verifier in verifiers:
      if verifier.name in pending.verifications:
        logging.warning(
            'Re-running verififer %s for issue %s' % (
                verifier.name, pending.issue))
      verifier.verify(pending)
      assert verifier.name in pending.verifications
      if pending.get_state() == base.IGNORED:
        assert pending.verifications[verifier.name].get_state() == base.IGNORED
        # Remove all the other verifiers since we need to keep it in the
        # 'datastore' to not retry this issue constantly.
        for key in pending.verifications.keys():
          if key != verifier.name:
            del pending.verifications[key]
        return False
      if pending.get_state() == base.FAILED:
        # Throw if it didn't pass, so the error message is not lost.
        raise base.DiscardPending(
            pending, pending.error_message() or cls.FAILED_NO_MESSAGE)
    return True

  def _last_minute_checks(self, pending):
    """Does last minute checks on Rietvld before committing a pending patch."""
    pending_data = self.context.rietveld.get_issue_properties(
        pending.issue, True)
    if pending_data['commit'] != True:
      raise base.DiscardPending(pending, None)
    if pending_data['closed'] != False:
      raise base.DiscardPending(pending, None)
    if pending.description != pending_data['description'].replace('\r', ''):
      raise base.DiscardPending(pending, self.DESCRIPTION_UPDATED)
    commit_user = set([self.context.rietveld.email])
    expected = set(pending.reviewers) - commit_user
    actual  = set(pending_data['reviewers']) - commit_user
    # Try to be nice, if there was a drive-by review and the new reviewer left
    # a lgtm, don't abort.
    def is_approver(r):
      return any(
          m.get('approval') for m in pending_data['messages']
          if m['sender'] == r)
    drivers_by = [r for r in (actual - expected) if not is_approver(r)]
    if drivers_by:
      # That annoying driver-by.
      raise base.DiscardPending(
          pending,
          'List of reviewers changed. %s did a drive-by without LGTM\'ing!' %
          ','.join(drivers_by))
    if pending.patchset != pending_data['patchsets'][-1]:
      raise base.DiscardPending(pending,
          'Commit queue failed due to new patchset.')

  def _close_issue(self, pending):
    """Closes a issue on Rietveld after a commit succeeded."""
    viewvc_url = self.context.checkout.get_settings('VIEW_VC')
    description = pending.description
    msg = 'Committed: %s' % pending.revision
    if viewvc_url:
      viewvc_url = '%s%s' % (viewvc_url.rstrip('/'), pending.revision)
      msg = 'Committed: %s' % viewvc_url
      description += '\n\n' + msg
    self.context.status.send(
        pending,
        { 'verification': 'commit',
          'payload': {
            'revision': pending.revision,
            'output': msg,
            'url': viewvc_url}})
    self.context.rietveld.close_issue(pending.issue)
    self.context.rietveld.update_description(pending.issue, description)
    self.context.rietveld.add_comment(
        pending.issue, 'Change committed as %s' % pending.revision)

  def _discard_pending(self, pending, message):
    """Discards a pending commit. Attach an optional message to the review."""
    logging.debug('_discard_pending(%s, %s)', pending.issue, message)
    try:
      if pending.get_state() != base.IGNORED:
        self.context.rietveld.set_flag(
            pending.issue, pending.patchset, 'commit', 'False')
    except urllib2.HTTPError, e:
      logging.error(
          'Failed to set the flag to False for %s with message %s' % (
            pending.pending_name(), message))
      traceback.print_stack()
      errors.send_stack(e)
    if message:
      try:
        self.context.rietveld.add_comment(pending.issue, message)
      except urllib2.HTTPError, e:
        logging.error(
            'Failed to add comment for %s with message %s' % (
              pending.pending_name(), message))
        traceback.print_stack()
        errors.send_stack(e)
      self.context.status.send(
          pending,
          { 'verification': 'abort',
            'payload': {
              'output': message }})
    try:
      self.queue.pending_commits.remove(pending)
    except ValueError:
      pass

  def _commit_patch(self, pending):
    """Commits the pending patch to the repository.

    Do the checkout and applies the patch.
    """
    try:
      # Make sure to apply on HEAD.
      pending.revision = None
      pending.apply_patch(self.context, True)
      commit_message = '%s\n\nReview URL: %s/%s' % (
          pending.description,
          self.context.rietveld.url,
          pending.issue)
      pending.revision = self.context.checkout.commit(
          commit_message, pending.owner)

      self.recent_commit_timestamps.append(time.time())
      self.recent_commit_timestamps = (
          self.recent_commit_timestamps[-(self.MAX_COMMIT_BURST + 1):])

      if not pending.revision:
        raise base.DiscardPending(pending, 'Failed to commit patch.')
      self._close_issue(pending)
    except (checkout.PatchApplicationFailed, patch.UnsupportedPatchFormat), e:
      raise base.DiscardPending(pending, str(e))
    except subprocess2.CalledProcessError, e:
      stdout = getattr(e, 'stdout', None)
      out = 'Failed to apply the patch.'
      if stdout:
        out += '\n%s' % stdout
      raise base.DiscardPending(pending, out)

  def _throttle(self, pending):
    """Returns True if a commit should be delayed."""
    if pending.postpone():
      return True
    if not self.recent_commit_timestamps:
      return False
    cutoff = time.time() - self.COMMIT_BURST_DELAY
    bursted = len([True for i in self.recent_commit_timestamps if i > cutoff])
    return bursted >= self.MAX_COMMIT_BURST

  def load(self, filename):
    """Loads the commit queue state from a JSON file."""
    self.queue = model.load_from_json_file(filename)
    self.queue.pending_commits = self.queue.pending_commits or []

  def save(self, filename):
    """Save the commit queue state in a simple JSON file."""
    model.save_to_json_file(filename, self.queue)
    self.context.status.close()
