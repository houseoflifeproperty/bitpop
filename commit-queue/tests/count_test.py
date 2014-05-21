#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for tools/count.py."""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(ROOT_DIR, '..')
sys.path.insert(0, PROJECT_DIR)


import find_depot_tools  # pylint: disable=W0611
import subprocess2


class TestCount(unittest.TestCase):
  def test_2011_04_09(self):
    # Verifies commits done on that day.
    # TODO(maruel): Import directly and do not use live data.
    expected = (
        "Getting data from 2011-04-09 for 1 days\n"
        "Top users:           3 out of      3 total users  100.00%\n"
        "  Committed          3 out of      3 CQ'ed commits 100.00%\n"
        "\n"
        "Total commits:                   26\n"
        "Total commits by commit bot:      3 (  11.5%)\n")
    exe_path = os.path.join(PROJECT_DIR, 'tools', 'count.py')
    args = [sys.executable, exe_path, '-s', '2011-04-09', '-d', '1', '-o']
    self.assertEquals(expected, subprocess2.check_output(args))


if __name__ == '__main__':
  unittest.main()
