# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A poller which consistently interleaves revisions across multiple branches.

SAMPLE USAGE:

Simple case:
  poller = GitBranchPoller(
    'https://chromium.googlesource.com/chromium/src.git',
    ['master', 'lkcr', 'lkgr'],
  )

  c['change_sources'] = [poller]

  This poller will poll the Chromium src repository for changes on the master,
  lkcr, and lkgr branches. New changes will be sent to the buildbot master.

Tag comparator:
  poller = GitBranchPoller(
    'https://chromium.googlesource.com/chromium/src.git',
    ['master', 'lkcr', 'lkgr'],
  )

  c['change_sources'] = [poller]

  master_utils.AutoSetupMaster(c, ActiveMaster, tagComparator=poller.comparator)

  This is the same as above, except the console view will sort revisions using
  the same logic as the poller, which allows for a consistent revision ordering.

Excluded refs:
  remote = GitBranchPoller.Remote(
    'upstream',
    'https://chromium.googlesource.com/chromium/src.git',
    {
      'refs/branch-heads/2062': 'refs/remotes/upstream/2062',
      'refs/branch-heads/1985': 'refs/remotes/upstream/1985',
    },
  )

  poller = GitBranchPoller(
    'https://chromium.googlesource.com/my_chromium_fork/src.git',
    ['master', '2062', '1985'],
    excluded_refs=['upstream/master', 'upstream/2062', 'upstream/1985'],
    additional_remotes=[remote],
  )

  c['change_sources'] = [poller]

  This poller can be used to poll My Chromium Fork's src repository for changes
  on the master, as well as the 2062 and 1985 release branches, while ignoring
  any revision history from the original Chromium src repository. This is useful
  for polling for changes that are unique to the fork.
"""

from buildbot.changes.base import PollingChangeSource
from buildbot.status.web.console import RevisionComparator
from buildbot.util import deferredLocked
from twisted.internet import defer, utils
from twisted.python import log

import datetime
import os
import shutil


class GitBranchPoller(PollingChangeSource):
  """Polls multiple branches in a git repository."""

  class GitBranchRevisionComparator(RevisionComparator):
    def __init__(self):
      """Initializes a new instance of the GitBranchRevisionComparator class."""
      super(GitBranchPoller.GitBranchRevisionComparator, self).__init__()
      self.revisions = {}

    def addRevisions(self, revisions):
      """Add revisions to the GitBranchRevisionComparator.

      Args:
        revisions: An ordered list of revisions without duplicates.
      """
      for revision in revisions:
        assert revision not in self.revisions
        self.revisions[revision] = len(self.revisions)

    def isRevisionEarlier(self, first, second):
      """Returns whether the first change is earlier than the second.

      Args:
        first: A change this GitBranchRevisionComparator is aware of.
        second: A change this GitBranchRevisionComparator is aware of.

      Returns:
        True if the first change's revision is earlier than the second's.
      """
      assert first.revision in self.revisions
      assert second.revision in self.revisions
      return self.revisions[first.revision] < self.revisions[second.revision]

    def isValidRevision(self, revision):
      """Returns whether or not the given revision is known.

      Args:
        revision: A revision.

      Returns:
        True if this GitBranchRevisionComparator knows about the given revision.
      """
      return revision in self.revisions

    def getSortingKey(self):
      """Returns a function which maps changes to their sorted order."""
      return lambda change: self.revisions[change.revision]

  class Remote(object):
    def __init__(self, name, repo_url, ref_map):
      """Initializes a new instance of the Remote class.

      Args:
        name: A name for this remote.
        repo_url: URL of the remote repository.
        ref_map: A mapping of additional refspecs in the remote repository to
          local refspecs which should be kept up-to-date.
      """
      self.name = name
      self.repo_url = repo_url
      self.ref_map = ref_map

  def __init__(self, repo_url, branches, pollInterval=60, revlinktmpl='',
               workdir='git_poller', verbose=False, excluded_refs=tuple(),
               additional_remotes=tuple()):
    """Initializes a new instance of the GitBranchPoller class.

    Args:
      repo_url: URL of the remote repository.
      branches: List of branches in the remote repository to track.
      pollInterval: Number of seconds between polling operations.
      revlinktmpl: String template, taking a single string parameter,
        used to generate a web link to a revision.
      workdir: Working directory for the poller to use.
      verbose: Emit actual git commands and their raw results.
      excluded_refs: List of refs to exclude from polling operations.
      additional_remotes: List of Remote instances to fetch during polling.
    """
    self.repo_url = repo_url
    assert branches, 'GitBranchPoller: at least one branch is required'
    self.branches = branches
    self.pollInterval = pollInterval
    self.revlinktmpl = revlinktmpl
    self.workdir = os.path.abspath(workdir)
    self.verbose = verbose
    self.excluded_refs = ['^%s' % ref for ref in excluded_refs]
    self.additional_remotes = additional_remotes

    if not os.path.exists(self.workdir):
      self._log('Creating working directory:', self.workdir)
      os.makedirs(self.workdir)
    else:
      self._log('Using existing working directory:', self.workdir)

    # Mapping of branch names to the latest observed revision.
    self.branch_heads = {branch: None for branch in branches}
    self.branch_heads_lock = defer.DeferredLock()

    # Revision comparator.
    self.comparator = self.GitBranchRevisionComparator()

  @deferredLocked('branch_heads_lock')
  @defer.inlineCallbacks
  def startService(self):
    def stop(err):
      self._log('Failed to initialize revision history for', self.repo_url)

      # In verbose mode, stderr has already been emitted.
      if not self.verbose and err.rstrip():
        self._log('stderr:\n%s' % err.rstrip())

      return self.stopService()

    self._log('Initializing revision history of', self.repo_url)

    out, err, ret = yield self._git(
      'rev-parse', '--git-dir', '--is-bare-repository')
    out = out.splitlines()

    # Git commands are executed from inside the working directory, meaning
    # that relative to where the command was executed, --git-dir should be ".".
    if ret or len(out) != 2 or out[0] != '.' or out[1] != 'true':
      self._log('Working directory did not contain a mirrored repository')
      shutil.rmtree(self.workdir)
      os.makedirs(self.workdir)
      should_clone = True
    else:
      should_clone = False

    if should_clone:
      self._log('Cloning mirror of', self.repo_url)
      out, err, ret = yield self._git('clone', '--mirror', self.repo_url, '.')
      if ret:
        yield stop(err)
        return

    out, err, ret = yield self._git('remote')
    if ret:
      yield stop(err)
      return

    for remote in out.splitlines():
      out, err, ret = yield self._git('remote', 'remove', remote)
      if ret:
        yield stop(err)
        return

    out, err, ret = yield self._git('remote', 'add', 'origin', self.repo_url)
    if ret:
      yield stop(err)
      return

    for remote in self.additional_remotes:
      self._log('Adding remote', remote.repo_url)

      out, err, ret = yield self._git(
        'remote', 'add', remote.name, remote.repo_url)
      if ret:
        yield stop(err)
        return

      for (remote_ref, local_ref) in remote.ref_map.iteritems():
        out, err, ret = yield self._git(
          'config',
          '--add',
          'remote.%s.fetch' % remote.name,
          '+%s:%s' % (remote_ref, local_ref),
        )
        if ret:
          yield stop(err)
          return

    yield self._log('Fetching origin for', self.repo_url)
    out, err, ret = yield self._git('fetch', '--all')
    if ret:
      yield stop(err)
      return

    new_branch_heads = {}

    for branch in self.branch_heads:
      out, err, ret = yield self._git('rev-parse', 'origin/%s' % branch)
      if ret:
        yield stop(err)
      self._log(branch, 'at', out.rstrip())
      new_branch_heads[branch] = out.rstrip()

    # Don't exclude the specified excluded_refs here so the
    # comparator has the complete picture. Only exclude in
    # the polling operation, so those refs don't get passed
    # to the master.
    out, err, ret = yield self._git(
      'rev-list',
      '--date-order',
      '--reverse',
      *new_branch_heads.values())
    if ret:
      yield stop(err)
    revisions = out.splitlines()

    # Now that all git operations have succeeded and the poll is complete,
    # update our view of the branch heads and revision order.
    self.branch_heads.update(new_branch_heads)
    self.comparator.addRevisions(revisions)

    yield PollingChangeSource.startService(self)

  @deferredLocked('branch_heads_lock')
  @defer.inlineCallbacks
  def poll(self):
    def log_error(err, ret, always_emit_error=False):
      if ret:
        self._log('Polling', self.repo_url, 'failed, retrying in',
                  self.pollInterval, 'seconds')
        # In verbose mode, stderr has already been emitted.
        if (not self.verbose or always_emit_error) and err.rstrip():
          self._log('stderr:\n%s' % err.rstrip())

      return ret

    self._log('Polling', self.repo_url)
    out, err, ret = yield self._git('fetch', '--all')
    if log_error(err, ret):
      return

    rev_list_args = []
    revision_branch_map = {}
    new_branch_heads = {}

    for branch, head in self.branch_heads.iteritems():
      rev_list_args.append('%s..origin/%s' % (head, branch))
      out, err, ret = yield self._git('rev-list', rev_list_args[-1])
      if log_error(err, ret):
        return
      revisions = out.splitlines()

      if revisions:
        self._log(branch, 'at', revisions[0])
        new_branch_heads[branch] = revisions[0]

        for revision in revisions:
          revision_branch_map[revision] = branch
      else:
        self._log('No new revisions for', branch)

    if not revision_branch_map:
      return

    rev_list_args.extend(self.excluded_refs)

    self._log('Determining total ordering of revisions')
    out, err, ret = yield self._git(
      'rev-list', '--date-order', '--reverse', *rev_list_args)
    if log_error(err, ret):
      return

    revisions = out.splitlines()
    change_data = {revision: {} for revision in revisions}

    for revision in revisions:
      if revision not in revision_branch_map:
        self._log('Saw unexpected revision:', revision)
        continue

      self._log('Retrieving commit info for', revision, 'on',
                revision_branch_map[revision])

      out, err, ret = yield self._git(
        'show', r'--format=%ae', '--quiet', revision)
      if log_error(err, ret):
        return
      change_data[revision]['author'] = out.rstrip()

      out, err, ret = yield self._git(
        'show', r'--format=%ct', '--quiet', revision)
      if log_error(err, ret):
        return
      change_data[revision]['timestamp'] = datetime.datetime.fromtimestamp(
        float(out.rstrip()))

      out, err, ret = yield self._git(
        'show', r'--format=%B', '--quiet', revision)
      if log_error(err, ret):
        return
      change_data[revision]['description'] = out.rstrip()

      out, err, ret = yield self._git(
        'diff-tree', '--name-only', '--no-commit-id', '-r', revision)
      if log_error(err, ret):
        return
      change_data[revision]['files'] = out.splitlines()

    for revision in revisions:
      try:
        yield self.master.addChange(
          author=change_data[revision]['author'],
          branch=revision_branch_map[revision],
          comments=change_data[revision]['description'],
          files=change_data[revision]['files'],
          repository=self.repo_url,
          revision=revision,
          revlink=self.revlinktmpl % revision,
          when_timestamp=change_data[revision]['timestamp'],
        )

        self.comparator.addRevisions([revision])
      except Exception as e:
        log_error(str(e), 1, always_emit_error=True)
        return

    # Now that all git operations have succeeded and the poll is complete,
    # update our view of the branch heads.
    self.branch_heads.update(new_branch_heads)

  @defer.inlineCallbacks
  def _git(self, *args):
    out, err, ret = yield utils.getProcessOutputAndValue(
      'git', args, path=self.workdir)

    if self.verbose:
      self._log('git', *args)
      if out.rstrip():
        self._log('stdout:\n%s' % out.rstrip())
      if err.rstrip():
        self._log('stderr:\n%s' % err.rstrip())
      if ret:
        self._log('retcode:', ret)

    defer.returnValue((out, err, ret))

  def _log(self, *args):
    log.msg('%s:' % self.__class__.__name__, *args)

  def describe(self):
    return '%s%s: polling: %s, watching branches: %s' % (
      self.__class__.__name__,
      '' if self.master else '[STOPPED (refer to log)]',
      self.repo_url,
      ', '.join(self.branches),
    )
