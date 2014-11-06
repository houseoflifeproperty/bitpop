#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test for common.gerrit's 'time.py'"""

import test_env  # pylint: disable=W0611
import unittest

from common.gerrit.time import ParseGerritTime, ToGerritTime
from datetime import datetime


class GerritTimeTestCase(unittest.TestCase):
  def testParseGerritTime(self):
    self.assertEquals(
        ParseGerritTime('2014-03-11 00:20:08.946000000'),
        datetime(
          year=2014,
          month=3,
          day=11,
          hour=0,
          minute=20,
          second=8,
          microsecond=946000))

  def testToGerritTime(self):
    self.assertEquals(
        ToGerritTime(
          datetime(
            year=2014,
            month=3,
            day=11,
            hour=0,
            minute=20,
            second=8,
            microsecond=946000)),
        '2014-03-11 00:20:08.946000000')

  def testSymmetry(self):
    self.assertEquals(
        ToGerritTime(
            ParseGerritTime(
                '2014-03-11 00:20:08.946000000')),
        '2014-03-11 00:20:08.946000000')

    dt = datetime(
        year=2014,
        month=3,
        day=11,
        hour=0,
        minute=20,
        second=8,
        microsecond=946000)
    self.assertEquals(
        ParseGerritTime(
          ToGerritTime(dt)),
        dt)


if __name__ == '__main__':
  unittest.main()
