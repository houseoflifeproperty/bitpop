#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for lkgr_finder testcases."""


import os
import sys
import unittest

lkgr_path = os.path.join(
    os.path.dirname(__file__),
    '..',
    '..',
    '..',
    'masters',
    'master.chromium.lkgr')
sys.path.insert(0, lkgr_path)
import lkgr_finder
import test_env  # pylint: disable=W0611


# Make lkgr_finder quiet on stdout.
lkgr_finder.VERBOSE = False


class LKGRCandidateTest(unittest.TestCase):
  def testSimpleSucceeds(self):
    build_history = [
      (1, {'m1': {'b1': True}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, 1)

  def testSimpleFails(self):
    build_history = [
      (1, {'m1': {'b1': False}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, -1)

  def testModerateSuccess(self):
    build_history = [
      (1, {'m1': {'b1': True}, 'm2': {'b2': True}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, 1)

  def testModerateFailsOne(self):
    build_history = [
      (1, {'m1': {'b1': True}, 'm2': {'b2': False}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, -1)

  def testModerateFailsTwo(self):
    build_history = [
      (1, {'m1': {'b1': False}, 'm2': {'b2': True}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, -1)

  def testMultipleRevHistory(self):
    build_history = [
      (4, {'m1': {'b1': True},  'm2': {'b2': True}}),
      (3, {'m1': {'b1': False}, 'm2': {'b2': True}}),
      (2, {'m1': {'b1': True},  'm2': {'b2': False}}),
      (1, {'m1': {'b1': False}, 'm2': {'b2': False}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, 4)

  def testMultipleSuccess(self):
    build_history = [
      (5, {'m1': {'b1': True},  'm2': {'b2': True}}),
      (4, {'m1': {'b1': True},  'm2': {'b2': True}}),
      (3, {'m1': {'b1': False}, 'm2': {'b2': True}}),
      (2, {'m1': {'b1': True},  'm2': {'b2': False}}),
      (1, {'m1': {'b1': False}, 'm2': {'b2': False}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, 5)

  def testMissingFails(self):
    build_history = [
      (5, {'m1': {'b1': True},  }),
      (4, {                     'm2': {'b2': True}}),
      (3, {'m1': {'b1': False}, 'm2': {'b2': True}}),
      (2, {'m1': {'b1': True},  'm2': {'b2': False}}),
      (1, {'m1': {'b1': False}, 'm2': {'b2': False}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, -1)

  def testMissingSuccess(self):
    build_history = [
      (6, {                     'm2': {'b2': True}}),
      (5, {'m1': {'b1': True},  }),
      (4, {                     'm2': {'b2': True}}),
      (3, {'m1': {'b1': False}, 'm2': {'b2': True}}),
      (2, {'m1': {'b1': True},  'm2': {'b2': False}}),
      (1, {'m1': {'b1': False}, 'm2': {'b2': False}}),
    ]
    lkgr_steps = {'m1': {'b1': ['step']}, 'm2': {'b2': ['step']}}
    candidate = lkgr_finder.FindLKGRCandidate(build_history, lkgr_steps)
    self.assertEquals(candidate, 5)


if __name__ == '__main__':
  unittest.main()
