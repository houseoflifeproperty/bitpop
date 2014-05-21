#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for gatekeeper testcases."""

import unittest

import test_env  # pylint: disable=W0611

from master import failures_notifier


class FailuresNotifierTest(unittest.TestCase):
  def testFailuresNotifierCreation(self):
    notifier = failures_notifier.FailuresNotifier(
        fromaddr='buildbot@test',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.')
    self.assertTrue(notifier)


if __name__ == '__main__':
  unittest.main()
