#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/reviewer_lgtm.py."""

import logging
import os
import re
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

from verification import base
from verification import reviewer_lgtm

# From tests/
import mocks


class ReviewerLgtmTest(mocks.TestCase):
  def testNoReviewerNoMessage(self):
    self._check(reviewer_lgtm.LgtmStatus.NO_REVIEWER)

  def testNoReviewer(self):
    self.pending.messages = [
        {'approval': False, 'sender': 'reviewer@example.com'} ]
    #self.pending.reviewers = ['reviewer@example.com']
    self._check(reviewer_lgtm.LgtmStatus.NO_REVIEWER)

  def testNoMessage(self):
    self.pending.reviewers = ['reviewer@example.com']
    self._check(reviewer_lgtm.LgtmStatus.NO_COMMENT)

  def testLgtmOwner(self):
    self.pending.messages = [
        {'approval': True, 'sender': self.pending.owner}
    ]
    self.pending.reviewers = [self.pending.owner]
    self._check(reviewer_lgtm.LgtmStatus.NO_LGTM)

  def testLgtmOk(self):
    self.pending.messages = [
        {'approval': True, 'sender': 'reviewer@example.com'} ]
    self.pending.reviewers = ['reviewer@example.com']
    self._check(None)

  def testLgtmWrongDomain(self):
    self.pending.messages = [
        {'approval': True, 'sender': 'georges@example2.com'} ]
    self.pending.reviewers = ['georges@example2.com']
    self._check(reviewer_lgtm.LgtmStatus.NO_LGTM)

  def testLgtmBlacklist(self):
    self.pending.messages = [
        {
          'approval': False, 'text': 'fix your stuff',
          'sender': 'reviewer@example.com'
        },
        {'approval': True, 'sender': 'commit-bot@example.com'},
    ]
    self.pending.reviewers = ['reviewer@example.com', 'commit-bot@example.com']
    self._check(reviewer_lgtm.LgtmStatus.NO_LGTM)

  def testTBR(self):
    self.pending.description = 'Webkit roll\nTBR='
    self._check(None)

  def _check(self, error_message):
    ver = reviewer_lgtm.ReviewerLgtmVerifier(
        [r'^[\-\w]+\@example\.com$'],
        [re.escape('commit-bot@example.com')])
    ver.verify(self.pending)
    ver.update_status([self.pending])
    name = reviewer_lgtm.ReviewerLgtmVerifier.name
    self.assertEquals(
        self.pending.verifications.keys(), [name])
    self.assertEquals(
        self.pending.verifications[name].error_message, error_message)
    if error_message:
      self.assertEquals(
          self.pending.verifications[name].get_state(), base.FAILED)
    else:
      self.assertEquals(
          self.pending.verifications[name].get_state(), base.SUCCEEDED)


if __name__ == '__main__':
  logging.basicConfig(
      level=[logging.WARNING, logging.INFO, logging.DEBUG][
        min(sys.argv.count('-v'), 2)],
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
