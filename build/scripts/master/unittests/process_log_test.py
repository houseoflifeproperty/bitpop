#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for log processor testcases.

These tests should be run from the directory in which the script lives, so it
can find its data/ directory.
"""

# Note: log processing is being moved to the slave, please look at
# scripts/slave/process_log_utils.py and
# scripts/slave/unittests/runtest_annotator_test.py

import filecmp
import json
import os
import shutil
import stat
import unittest

import test_env

from master import chromium_step
from common import chromium_utils
from master.log_parser import process_log

import mock


# pylint: disable=W0212

TEST_PERCENTILES = [.05, .3, .8]

def _RemoveOutputDir():
  if os.path.exists('output_dir'):
    shutil.rmtree('output_dir')


class GoogleLoggingStepTest(unittest.TestCase):
  """ Logging testcases superclass

  The class provides some operations common for testcases.
  """
  def setUp(self):
    super(GoogleLoggingStepTest, self).setUp()
    _RemoveOutputDir()
    self._revision = 12345
    self._webkit_revision = 67890
    self._report_link = 'http://localhost/~user/report.html'
    self._output_dir = 'output_dir'
    self._log_processor_class = None

  def tearDown(self):
    if os.path.exists(self._output_dir):
      directoryListing = os.listdir(self._output_dir)
      for filename in directoryListing:
        file_stats = os.stat(os.path.join(self._output_dir, filename))
        self._assertReadable(file_stats)
    _RemoveOutputDir()
    super(GoogleLoggingStepTest, self).tearDown()

  def _assertReadable(self, file_stats):
    mode = file_stats[stat.ST_MODE]
    self.assertEqual(4, mode & stat.S_IROTH)

  def _ConstructStep(self, log_processor_class, logfile,
                     factory_properties=None, perf_expectations_path=None):
    """ Common approach to construct chromium_step.ProcessLogTestStep
    type instance with LogFile instance set.
    Args:
      log_processor_class: type/class of type chromium_step.ProcessLogTestStep
        that is going to be constructed. E.g. PagecyclerTestStep
      logfile: filename with setup process log output.
    """
    factory_properties = factory_properties or {}
    self._log_processor_class = chromium_utils.InitializePartiallyWithArguments(
        log_processor_class, factory_properties=factory_properties,
        report_link=self._report_link, output_dir=self._output_dir,
        perf_name='test-system', test_name='test-name',
        perf_filename=perf_expectations_path)
    step = chromium_step.ProcessLogShellStep(self._log_processor_class)
    log_file = self._LogFile(
        'stdio', open(os.path.join(test_env.DATA_PATH, logfile)).read())
    self._SetupBuild(step, self._revision, self._webkit_revision, log_file)
    return step

  def _SetupBuild(self, step, revision, webkit_revision, log_file):
    class BuildMock(mock.Mock):
      def __init__(self, revision, webkit_revision, log_files):
        mock.Mock.__init__(self)
        self._revision = revision
        self._webkit_revision = webkit_revision
        self._getLogsCalled = 0
        self._log_files = log_files

      def getProperty(self, property_name):
        if property_name == 'got_revision':
          return self._revision
        if property_name == 'got_webkit_revision':
          return self._webkit_revision

      def getLogs(self):
        self._getLogsCalled += 1
        if self._getLogsCalled > 1:
          raise Exception('getLogs called more than once')
        return self._log_files

    build_mock = BuildMock(revision, webkit_revision, [log_file])
    step.step_status = build_mock
    step.build = build_mock

  def _LogFile(self, name, content):
    class LogMock(mock.Mock):
      def __init__(self, name, content):
        mock.Mock.__init__(self)
        self._name = name
        self._content = content

      def getName(self):
        return self._name

      def getText(self):
        return self._content

    log_file_mock = LogMock(name, content)
    return log_file_mock


class BenchpressPerformanceTestStepTest(GoogleLoggingStepTest):

  def testPrependsSummaryBenchpress(self):
    files_that_are_prepended = ['summary.dat']
    os.mkdir('output_dir')
    for filename in files_that_are_prepended:
      filename = os.path.join('output_dir', filename)
      control_line = 'this is a line one, should become line two'
      with open(filename, 'w') as f:
        f.write(control_line)
      step = self._ConstructStep(process_log.BenchpressLogProcessor,
                                'benchpress_log')
      step.commandComplete('mycommand')

      self.assert_(os.path.exists(filename))
      text = open(filename).read()
      self.assert_(len(text.splitlines()) > 1,
                   'File %s was not prepended' % filename)
      self.assertEqual(control_line, text.splitlines()[1],
                       'File %s was not prepended' % filename)

  def testBenchpressSummary(self):
    step = self._ConstructStep(process_log.BenchpressLogProcessor,
                               'benchpress_log')
    step.commandComplete('mycommand')

    self.assert_(os.path.exists('output_dir/summary.dat'))
    actual = open('output_dir/summary.dat').readline()
    expected = '12345 469 165 1306 64 676 38 372 120 232 294 659 1157 397\n'
    self.assertEqual(expected, actual)

  def testCreateReportLink(self):
    class StepMock(mock.Mock):
      def __init__(self, urltype, reportlink):
        mock.Mock.__init__(self)
        self._urltype = urltype
        self._reportlink = reportlink
        self._addURLCalled = 0

      def addURL(self, urltype, link):
        self._addURLCalled += 1
        if self._addURLCalled > 1:
          raise Exception('getLogs called more than once')
        if urltype != self._urltype:
          raise Exception('url_type should be \'%s\'' % self._urltype)
        if link != self._reportlink:
          raise Exception('link should have been \'%s\'' % self._reportlink)

    log_processor_class = chromium_utils.InitializePartiallyWithArguments(
        process_log.BenchpressLogProcessor, report_link=self._report_link,
        output_dir=self._output_dir)
    step = chromium_step.ProcessLogShellStep(log_processor_class)
    build_mock = mock.Mock()
    source_mock = mock.Mock()
    change_mock = mock.Mock()
    change_mock.revision = self._revision
    source_mock.changes = [change_mock]
    build_mock.source = source_mock
    step_status = StepMock('results', log_processor_class().ReportLink())
    step.build = build_mock
    step.step_status = step_status
    step._CreateReportLinkIfNeccessary()
    build_mock.verify()

# A class for enabling setting different percentiles for GraphingLogProcessor.
class TestGraphingLogProcessor(process_log.GraphingLogProcessor):
  def __init__(self, *args, **kwargs):
    process_log.GraphingLogProcessor.__init__(self, *args, **kwargs)
    self._percentiles = TEST_PERCENTILES

class GraphingLogProcessorTest(GoogleLoggingStepTest):

  def _TestPerfExpectations(self, perf_expectations_file):
    perf_expectations_path = os.path.join(
        test_env.DATA_PATH, perf_expectations_file)
    step = self._ConstructStep(TestGraphingLogProcessor,
                               'graphing_processor.log',
                               factory_properties={'expectations': True,
                                                   'perf_id': 'tester'},
                               perf_expectations_path=perf_expectations_path)
    step.commandComplete('mycommand')
    actual_file = os.path.join('output_dir', 'graphs.dat')
    self.assert_(os.path.exists(actual_file))
    actual = json.load(open(actual_file))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, 'graphing_processor-graphs.dat')))
    self.assertEqual(expected, actual)
    return step

  def testSummary(self):
    step = self._ConstructStep(TestGraphingLogProcessor,
                               'graphing_processor.log')
    step.commandComplete('mycommand')
    for graph in ('commit_charge', 'ws_final_total', 'vm_final_browser',
                  'vm_final_total', 'ws_final_browser', 'processes',
                  'artificial_graph'):
      filename = '%s-summary.dat' % graph
      self.assert_(os.path.exists(os.path.join('output_dir', filename)))
      # Since the output files are JSON-encoded, they may differ in form, but
      # represent the same data. Therefore, we decode them before comparing.
      actual = json.load(open(os.path.join('output_dir', filename)))
      expected = json.load(open(os.path.join(test_env.DATA_PATH, filename)))
      self.assertEqual(expected, actual)

  def testFrameRateSummary(self):
    step = self._ConstructStep(process_log.GraphingFrameRateLogProcessor,
                               'frame_rate_graphing_processor.log')
    step.commandComplete('mycommand')
    for graph in ('blank', 'googleblog'):
      filename = '%s-summary.dat' % graph
      self.assert_(os.path.exists(os.path.join('output_dir', filename)))
      # Since the output files are JSON-encoded, they may differ in form, but
      # represent the same data. Therefore, we decode them before comparing.
      actual = json.load(open(os.path.join('output_dir', filename)))
      expected = json.load(
          open(os.path.join(test_env.DATA_PATH, 'frame_rate', filename)))
      self.assertEqual(expected, actual)

  def testFrameRateGestureList(self):
    step = self._ConstructStep(process_log.GraphingFrameRateLogProcessor,
                               'frame_rate_graphing_processor.log')
    step.commandComplete('mycommand')
    for graph in ('blank', 'googleblog'):
      for trace in ('fps', 'fps_ref'):
        filename = "%s_%s_%s.dat" % (self._revision, graph, trace)
        self.assert_(os.path.exists(os.path.join('output_dir', filename)))
        actual = os.path.join('output_dir', filename)
        expected = os.path.join(test_env.DATA_PATH, 'frame_rate', filename)
        self.assert_(filecmp.cmp(actual, expected))

  def testGraphList(self):
    step = self._ConstructStep(TestGraphingLogProcessor,
                               'graphing_processor.log')
    step.commandComplete('mycommand')
    actual_file = os.path.join('output_dir', 'graphs.dat')
    self.assert_(os.path.exists(actual_file))
    actual = json.load(open(actual_file))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, 'graphing_processor-graphs.dat')))
    self.assertEqual(expected, actual)

  def testPerfExpectationsImproveRelative(self):
    step = self._TestPerfExpectations('perf_improve_relative.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.00%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressRelative(self):
    step = self._TestPerfExpectations('perf_regress_relative.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (50.00%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveRelativeFloat(self):
    step = self._TestPerfExpectations('perf_improve_relative_float.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.10%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveRelativeFloatNonSci(self):
    step = self._TestPerfExpectations(
        'perf_improve_relative_float_nonscientific.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.10%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressRelativeFloat(self):
    step = self._TestPerfExpectations('perf_regress_relative_float.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (49.96%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsolute(self):
    step = self._TestPerfExpectations('perf_regress_absolute.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.49%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveAbsolute(self):
    step = self._TestPerfExpectations('perf_improve_absolute.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (3.20%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsoluteFloat(self):
    step = self._TestPerfExpectations('perf_regress_absolute_float.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.55%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsoluteFloatNonSci(self):
    step = self._TestPerfExpectations(
        'perf_regress_absolute_float_nonscientific.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.55%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveAbsoluteFloat(self):
    step = self._TestPerfExpectations('perf_improve_absolute_float.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (3.21%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeRelative(self):
    step = self._TestPerfExpectations('perf_nochange_relative.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeAbsolute(self):
    step = self._TestPerfExpectations('perf_nochange_absolute.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeRelativeFloat(self):
    step = self._TestPerfExpectations('perf_nochange_relative_float.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeAbsoluteFloat(self):
    step = self._TestPerfExpectations('perf_nochange_absolute_float.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerSuccess(self):
    step = self._TestPerfExpectations('perf_test_better_lower_success.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerImprove(self):
    step = self._TestPerfExpectations('perf_test_better_lower_improve.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerRegress(self):
    step = self._TestPerfExpectations('perf_test_better_lower_regress.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherSuccess(self):
    step = self._TestPerfExpectations('perf_test_better_higher_success.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(0, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherImprove(self):
    step = self._TestPerfExpectations('perf_test_better_higher_improve.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherRegress(self):
    step = self._TestPerfExpectations('perf_test_better_higher_regress.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressZero(self):
    step = self._TestPerfExpectations(
        'perf_test_better_lower_regress_zero.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (inf%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(2, step._log_processor.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveZero(self):
    step = self._TestPerfExpectations(
        'perf_test_better_higher_improve_zero.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (inf%)')
    self.assertEqual(expected, step._result_text[0])
    self.assertEqual(1, step._log_processor.evaluateCommand('mycommand'))

  def testHistogramGeometricMeanAndStandardDeviation(self):
    step = self._ConstructStep(TestGraphingLogProcessor,
                               'graphing_processor.log')
    step.commandComplete('mycommand')
    filename = 'hist1-summary.dat'
    self.assert_(os.path.exists(os.path.join('output_dir', filename)))
    # Since the output files are JSON-encoded, they may differ in form, but
    # represent the same data. Therefore, we decode them before comparing.
    actual = json.load(open(os.path.join('output_dir', filename)))
    expected = json.load(open(os.path.join(test_env.DATA_PATH, filename)))
    self.assertEqual(expected, actual)

  def testHistogramPercentiles(self):
    step = self._ConstructStep(TestGraphingLogProcessor,
                               'graphing_processor.log')
    step.commandComplete('mycommand')
    graphs = ['hist1_%s' % str(p) for p in TEST_PERCENTILES]
    for graph in graphs:
      filename = '%s-summary.dat' % graph
      self.assert_(os.path.exists(os.path.join('output_dir', filename)))
      # Since the output files are JSON-encoded, they may differ in form, but
      # represent the same data. Therefore, we decode them before comparing.
      actual = json.load(open(os.path.join('output_dir', filename)))
      expected = json.load(open(os.path.join(test_env.DATA_PATH, filename)))
      self.assertEqual(expected, actual)


if __name__ == '__main__':
  unittest.main()
