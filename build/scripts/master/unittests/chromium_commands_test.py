#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_commands testcases."""

import unittest

import json
import test_env  # pylint: disable=W0611

from master.factory.chromium_commands import ChromiumCommands
from master.factory.commands import FactoryCommands


class ChromiumCommandsTest(unittest.TestCase):

  def setUp(self):
    self.cmd = ChromiumCommands()

  def testAddFactorySimple(self):
    newcmd = FactoryCommands().AddFactoryProperties(None)
    passed = json.loads(newcmd[-1].split('=', 1)[1])
    self.assert_(passed == {})

  def testAddFactoryComplex(self):
    oldcmd = ['FOOBIE', 'BARBIE']
    props = {
        'B': True,
        'A': 'Flarge',
        'C': {'Noodle': '{"A":"B","C":"D"}', 'Soup': 'Nuts'},
        'X': None}
    newcmd = FactoryCommands().AddFactoryProperties(props, oldcmd)
    # Check for side-effects
    self.assert_(oldcmd == newcmd)
    self.assert_(oldcmd[1] == 'BARBIE')
    # Check for parameter name
    self.assert_(newcmd[-1].startswith('--factory-properties'))
    # Check for invertible encoding
    passed = json.loads(newcmd[-1].split('=', 1)[1])
    self.assert_(props == passed)

if __name__ == '__main__':
  unittest.main()
