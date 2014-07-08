#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for lkgr_finder testcases."""


import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', '..'))
from tools import lkgr_finder


# Make lkgr_finder quiet on stdout.
lkgr_finder.VERBOSE = False


class LKGRCandidateTest(unittest.TestCase):
  def testSimpleSucceeds(self):
    build_history = {'m1': {'b1': [(1, True, 1)]}}
    revisions = [1]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, 1)

  def testSimpleFails(self):
    build_history = {'m1': {'b1': [(1, False, 1)]}}
    revisions = [1]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, None)

  def testModerateSuccess(self):
    build_history = {
        'm1': {'b1': [(1, True, 1)]},
        'm2': {'b2': [(1, True, 1)]}}
    revisions = [1]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, 1)

  def testModerateFailsOne(self):
    build_history = {
        'm1': {'b1': [(1, True, 1)]},
        'm2': {'b2': [(1, False, 1)]}}
    revisions = [1]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, None)

  def testModerateFailsTwo(self):
    build_history = {
        'm1': {'b1': [(1, False, 1)]},
        'm2': {'b2': [(1, True, 1)]}}
    revisions = [1]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, None)

  def testMultipleRevHistory(self):
    build_history = {
        'm1': {'b1': [(1, False, 1), (2, True, 2),
                      (3, False, 3), (4, True, 4)]},
        'm2': {'b2': [(1, False, 1), (2, False, 2),
                      (3, True, 3), (4, True, 4)]}}
    revisions = [1, 2, 3, 4]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, 4)

  def testMultipleSuccess(self):
    build_history = {
        'm1': {'b1': [(1, False, 1), (2, True, 2),
                      (3, False, 3), (4, True, 4), (5, True, 5)]},
        'm2': {'b2': [(1, False, 1), (2, False, 2),
                      (3, True, 3), (4, True, 4), (5, True, 5)]}}
    revisions = [1, 2, 3, 4, 5]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, 5)

  def testMissingFails(self):
    build_history = {
        'm1': {'b1': [(1, False, 1), (2, True, 2),
                      (3, False, 3), (5, True, 5)]},
        'm2': {'b2': [(1, False, 1), (2, False, 2),
                      (3, True, 3), (4, True, 4)]}}
    revisions = [1, 2, 3, 4, 5]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, None)

  def testMissingSuccess(self):
    build_history = {
        'm1': {'b1': [(1, False, 1), (2, True, 2),
                      (3, False, 3), (5, True, 5)]},
        'm2': {'b2': [(1, False, 1), (2, False, 2),
                      (3, True, 3), (4, True, 4), (6, True, 6)]}}
    revisions = [1, 2, 3, 4, 5, 6]
    candidate = lkgr_finder.FindLKGRCandidate(
        build_history, revisions, lkgr_finder.SvnRevisionCmp)
    self.assertEquals(candidate, 5)


if __name__ == '__main__':
  unittest.main()
