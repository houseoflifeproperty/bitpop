#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_commands testcases."""

import unittest

import json
import test_env  # pylint: disable=W0611

from master.factory.chromium_commands import ChromiumCommands
from master.factory.commands import CreatePerformanceStepClass
from master.factory.commands import FactoryCommands
from master.log_parser import process_log


class ChromiumCommandsTest(unittest.TestCase):

  def setUp(self):
    self.cmd = ChromiumCommands()
    self.log_processor_class = process_log.PerformanceLogProcessor
    self.report_link = 'http://localhost/report.html'
    self.output_dir = 'output-dir'

  def testCreatePerformanceStepClass(self):
    # pylint: disable=W0212
    performanceStepClass = CreatePerformanceStepClass(
        self.log_processor_class, self.report_link, self.output_dir)
    performanceStep = performanceStepClass() # initialize
    self.assert_(performanceStep._log_processor)
    log_processor = performanceStep._log_processor
    self.assertEqual(self.report_link, log_processor._report_link)
    self.assertEqual(self.output_dir, log_processor._output_dir)

  def testCreatePerformanceStepClassWithMissingReportLinkArguments(self):
    # pylint: disable=W0212
    performanceStepClass = CreatePerformanceStepClass(self.log_processor_class)
    performanceStep = performanceStepClass() # initialize
    self.assert_(performanceStep._log_processor)
    log_processor = performanceStep._log_processor
    self.assert_(not log_processor._report_link)
    self.assert_(log_processor._output_dir)

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
