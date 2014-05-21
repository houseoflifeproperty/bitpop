# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Look for a LGTM in the messages from a valid reviewer."""

import logging
import re

from verification import base


def _regexp_check(value, whitelist, blacklist):
  """Returns True if value passes whitelist and not blacklist.

  Both whitelist and blacklist are a list of regexp strings.
  """
  def match(value, checklist):
    return any(re.match(i, value) for i in checklist)
  return match(value, whitelist) and not match(value, blacklist)


class LgtmStatus(base.SimpleStatus):
  NO_REVIEWER = 'No reviewers yet.'
  NO_COMMENT = 'No comments yet.'
  NO_LGTM = (
      'No LGTM from a valid reviewer yet. Only full committers are accepted.\n'
      'Even if an LGTM may have been provided, it was from a non-committer or\n'
      'a lowly provisional committer, _not_ a full super star committer.\n'
      'See http://www.chromium.org/getting-involved/become-a-committer\n'
      'Note that this has nothing to do with OWNERS files.')

  def __init__(self, pending=None, whitelist=None, blacklist=None):
    super(LgtmStatus, self).__init__()
    # Can't save 'pending' reference here but postpone() will need it as a
    # parameter.
    if pending:
      self._check(pending, whitelist, blacklist)

  def _check(self, pending, whitelist, blacklist):
    """Updates self.state and self.error_message properties."""
    # The owner cannot be a reviewer.
    blacklist_owner = blacklist + [re.escape(pending.owner)]

    if self._is_tbr(pending):
      logging.debug('Change %s is TBR' % pending.issue)
      if _regexp_check(pending.owner, whitelist, blacklist):
        # TBR changes from a committer are fine.
        self.state = base.SUCCEEDED
        return

    if not pending.reviewers:
      self.error_message = self.NO_REVIEWER
      self.state = base.FAILED
      return

    if not pending.messages:
      self.error_message = self.NO_COMMENT
      self.state = base.FAILED
      return

    def match_reviewer(r):
      return _regexp_check(r, whitelist, blacklist_owner)

    for i in pending.messages:
      if i['approval'] and match_reviewer(i['sender']):
        logging.info('Found lgtm by %s' % i['sender'])
        self.state = base.SUCCEEDED
        return

    # TODO: Force a refresh of the meta data and use postpone() instead of
    # bailing out if there is a valid reviewer that hasn't replied yet.
    self.error_message = self.NO_LGTM
    self.state = base.FAILED

  @staticmethod
  def _is_tbr(pending):
    """Returns True if a description contains TBR=.

    This function should be moved elsewhere.
    """
    return bool(re.search(r'^TBR=.*$', pending.description, re.MULTILINE))


class ReviewerLgtmVerifier(base.Verifier):
  """Needs at least one reviewer matching at least one regexp in
  self.reviewers that is not also the owner of the issue.
  """
  name = 'reviewer_lgtm'

  def __init__(self, whitelist, blacklist):
    super(ReviewerLgtmVerifier, self).__init__()
    self.whitelist = whitelist
    self.blacklist = blacklist

  def verify(self, pending):
    pending.verifications[self.name] = LgtmStatus(
        pending=pending, whitelist=self.whitelist, blacklist=self.blacklist)

  def update_status(self, queue):
    pass
