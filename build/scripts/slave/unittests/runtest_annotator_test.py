#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for annotated log parsers (aka log processors) used by runtest.py.

The classes tested here reside in process_log_utils.py.

The script runtest.py has the option to parse test output locally and send
results to the master via annotator steps. This file tests those parsers.
"""

import json
import os
import unittest

import test_env  # pylint: disable=W0403,W0611

from slave import process_log_utils

# These should be the same as the constants used in process_log_utils.
# See: http://docs.buildbot.net/current/developer/results.html
SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(6)

# Custom percentile numbers to use in the tests below.
TEST_PERCENTILES = [.05, .3, .8]


class LogProcessorTest(unittest.TestCase):
  """Base class for log processor unit tests. Contains common operations."""

  def setUp(self):
    """Set up for all test method of each test method below."""
    super(LogProcessorTest, self).setUp()
    self._revision = 12345
    self._webkit_revision = 67890

  def _ConstructDefaultProcessor(
      self, log_processor_class, factory_properties=None,
      perf_expectations_path=None):
    """Creates a log processor instance.

    Args:
      log_processor_class: A sub-class of PerformanceLogProcessor.
      factory_properties: A dictionary of properties (optional).
      perf_expectations_path: Expectations file path (optional).

    Returns:
      An instance of the given log processor class.
    """
    factory_properties = factory_properties or {}
    factory_properties['perf_filename'] = perf_expectations_path
    factory_properties['perf_name'] = 'test-system'
    factory_properties['test_name'] = 'test-name'
    processor = log_processor_class(
        revision=self._revision, build_properties={},
        factory_properties=factory_properties,
        webkit_revision=self._webkit_revision)

    # Set custom percentiles. This will be used by GraphingLogProcessor, which
    # has and uses a private member attribute called _percentiles.
    if hasattr(processor, '_percentiles'):
      processor._percentiles = TEST_PERCENTILES

    return processor

  def _ProcessLog(self, log_processor, logfile):  # pylint: disable=R0201
    """Reads in a input log file and processes it.

    This changes the state of the log processor object; the output is stored
    in the object and can be gotten using the PerformanceLogs() method.

    Args:
      log_processor: An PerformanceLogProcessor instance.
      logfile: File name of an input performance results log file.
    """
    for line in open(os.path.join(test_env.DATA_PATH, logfile)):
      log_processor.ProcessLine(line)

  def _CheckFileExistsWithData(self, logs, targetfile):
    """Asserts that |targetfile| exists in the |logs| dict and is non-empty."""
    self.assertTrue(targetfile in logs, 'File %s was not output.' % targetfile)
    self.assertTrue(logs[targetfile], 'File %s did not contain data.' %
                    targetfile)

  def _ConstructParseAndCheckLogfiles(
      self, inputfiles, logfiles, log_processor_class, *args, **kwargs):
    """Uses a log processor to process the given input files.

    Args:
      inputfiles: A list of input performance results log file names.
      logfiles: List of expected output ".dat" file names.
      log_processor_class: The log processor class to use.

    Returns:
      A dictionary mapping output file name to output file lines.
    """
    parser = self._ConstructDefaultProcessor(
        log_processor_class, *args, **kwargs)
    for inputfile in inputfiles:
      self._ProcessLog(parser, inputfile)

    logs = parser.PerformanceLogs()
    for logfile in logfiles:
      self._CheckFileExistsWithData(logs, logfile)

    return logs

  def _ConstructParseAndCheckJSON(
      self, inputfiles, logfiles, subdir, log_processor_class, *args, **kwargs):
    """Processes input with a log processor and checks against expectations.

    Args:
      inputfiles: A list of input performance result log file names.
      logfiles: A list of expected output ".dat" file names.
      subdir: Subdirectory containing expected output files.
      log_processor_class: A log processor class.
    """
    logs = self._ConstructParseAndCheckLogfiles(
        inputfiles, logfiles, log_processor_class, *args, **kwargs)
    for filename in logfiles:
      actual = json.loads('\n'.join(logs[filename]))
      if subdir:
        path = os.path.join(test_env.DATA_PATH, subdir, filename)
      else:
        path = os.path.join(test_env.DATA_PATH, filename)
      expected = json.load(open(path))
      self.assertEqual(expected, actual, 'JSON data in %s did not match '
          'expectations.' % filename)


class GraphingLogProcessorTest(LogProcessorTest):
  """Test case for basic functionality of GraphingLogProcessor class."""

  def testSummary(self):
    """Tests the output of "summary" files, which contain per-graph data."""
    input_files = ['graphing_processor.log']
    output_files = ['%s-summary.dat' % graph for graph in ('commit_charge',
        'ws_final_total', 'vm_final_browser', 'vm_final_total',
        'ws_final_browser', 'processes', 'artificial_graph')]

    self._ConstructParseAndCheckJSON(input_files, output_files, None,
        process_log_utils.GraphingLogProcessor)

  def testGraphList(self):
    """Tests the output of "graphs.dat" files, which contains a graph list."""
    input_files = ['graphing_processor.log']
    graphfile = 'graphs.dat'
    output_files = [graphfile]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor)

    actual = json.loads('\n'.join(logs[graphfile]))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, 'graphing_processor-graphs.dat')))

    self.assertEqual(len(actual), len(expected))

    for graph in expected:
      self.assertTrue(graph['name'] in actual)
      for element in graph:
        self.assertEqual(actual[graph['name']][element], graph[element])

  def testHistogramGeometricMeanAndStandardDeviation(self):
    input_files = ['graphing_processor.log']
    summary_file = 'hist1-summary.dat'
    output_files = [summary_file]

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor)

    actual = json.loads('\n'.join(logs[summary_file]))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, summary_file)))

    self.assertEqual(actual, expected, 'Filename %s did not contain expected '
        'data.' % summary_file)

  def testHistogramPercentiles(self):
    input_files = ['graphing_processor.log']
    summary_files = ['hist1_%s-summary.dat' % str(p) for p in TEST_PERCENTILES]
    output_files = summary_files

    logs = self._ConstructParseAndCheckLogfiles(input_files, output_files,
        process_log_utils.GraphingLogProcessor)

    for filename in output_files:
      actual = json.loads('\n'.join(logs[filename]))
      expected = json.load(open(os.path.join(test_env.DATA_PATH, filename)))
      self.assertEqual(actual, expected, 'Filename %s did not contain expected '
          'data.' % filename)


class GraphingLogProcessorPerfTest(LogProcessorTest):
  """Another test case for the GraphingLogProcessor class.

  The tests in this test case compare results against the contents of a
  perf expectations file.
  """

  def _TestPerfExpectations(self, perf_expectations_file):
    perf_expectations_path = os.path.join(
        test_env.DATA_PATH, perf_expectations_file)

    input_file = 'graphing_processor.log'
    graph_file = 'graphs.dat'

    parser = self._ConstructDefaultProcessor(
        process_log_utils.GraphingLogProcessor,
        factory_properties={'expectations': True, 'perf_id': 'tester'},
        perf_expectations_path=perf_expectations_path)

    self._ProcessLog(parser, input_file)

    actual = json.loads('\n'.join(parser.PerformanceLogs()[graph_file]))
    expected = json.load(open(
        os.path.join(test_env.DATA_PATH, 'graphing_processor-graphs.dat')))

    self.assertEqual(len(actual), len(expected))

    for graph in expected:
      self.assertTrue(graph['name'] in actual)
      for element in graph:
        self.assertEqual(actual[graph['name']][element], graph[element])
    return parser

  def testPerfExpectationsImproveRelative(self):
    step = self._TestPerfExpectations('perf_improve_relative.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.00%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressRelative(self):
    step = self._TestPerfExpectations('perf_regress_relative.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (50.00%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveRelativeFloat(self):
    step = self._TestPerfExpectations('perf_improve_relative_float.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.10%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveRelativeFloatNonSci(self):
    step = self._TestPerfExpectations(
        'perf_improve_relative_float_nonscientific.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (25.10%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressRelativeFloat(self):
    step = self._TestPerfExpectations('perf_regress_relative_float.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (49.96%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsolute(self):
    step = self._TestPerfExpectations('perf_regress_absolute.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.49%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveAbsolute(self):
    step = self._TestPerfExpectations('perf_improve_absolute.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (3.20%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsoluteFloat(self):
    step = self._TestPerfExpectations('perf_regress_absolute_float.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.55%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressAbsoluteFloatNonSci(self):
    step = self._TestPerfExpectations(
        'perf_regress_absolute_float_nonscientific.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (2.55%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveAbsoluteFloat(self):
    step = self._TestPerfExpectations('perf_improve_absolute_float.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (3.21%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeRelative(self):
    step = self._TestPerfExpectations('perf_nochange_relative.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(SUCCESS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeAbsolute(self):
    step = self._TestPerfExpectations('perf_nochange_absolute.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(SUCCESS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeRelativeFloat(self):
    step = self._TestPerfExpectations('perf_nochange_relative_float.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(SUCCESS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsNochangeAbsoluteFloat(self):
    step = self._TestPerfExpectations('perf_nochange_absolute_float.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(SUCCESS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerSuccess(self):
    step = self._TestPerfExpectations('perf_test_better_lower_success.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(SUCCESS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerImprove(self):
    step = self._TestPerfExpectations('perf_test_better_lower_improve.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterLowerRegress(self):
    step = self._TestPerfExpectations('perf_test_better_lower_regress.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherSuccess(self):
    step = self._TestPerfExpectations('perf_test_better_higher_success.json')
    expected = ('12t_cc: 50.2k')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(SUCCESS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherImprove(self):
    step = self._TestPerfExpectations('perf_test_better_higher_improve.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))

  def testPerfExpectationsBetterHigherRegress(self):
    step = self._TestPerfExpectations('perf_test_better_higher_regress.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (0.01%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsRegressZero(self):
    step = self._TestPerfExpectations(
        'perf_test_better_lower_regress_zero.json')
    expected = ('PERF_REGRESS: vm_final_browser/1t_vm_b (inf%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(FAILURE, step.evaluateCommand('mycommand'))

  def testPerfExpectationsImproveZero(self):
    step = self._TestPerfExpectations(
        'perf_test_better_higher_improve_zero.json')
    expected = ('PERF_IMPROVE: vm_final_browser/1t_vm_b (inf%)')
    self.assertEqual(expected, step.PerformanceSummary()[0])
    self.assertEqual(WARNINGS, step.evaluateCommand('mycommand'))


class GraphingPageCyclerLogProcessorPerfTest(LogProcessorTest):
  """Unit tests for the GraphingPageCyclerLogProcessor class."""

  def testPageCycler(self):
    parser = self._ConstructDefaultProcessor(
        process_log_utils.GraphingPageCyclerLogProcessor)
    self._ProcessLog(parser, 'page_cycler.log')

    expected = 't: 2.32k'
    self.assertEqual(expected, parser.PerformanceSummary()[0])


class GraphingEndureLogProcessorTest(LogProcessorTest):
  """Unit tests for the GraphingEndureLogProcessor class."""

  def testProcessLogs(self):
    log_processor = self._ConstructDefaultProcessor(
        process_log_utils.GraphingEndureLogProcessor)

    # Process the sample endure output log file.
    self._ProcessLog(log_processor, 'endure_sample.log')
    output = log_processor.PerformanceLogs()

    # The data in the input sample file is considered to have 3 separate
    # graph names, so there are 3 entries here.
    self.assertEqual(3, len(output))

    # Each of these three entries is mapped to a list that contains one string.
    self.assertEqual(1, len(output['object_counts-summary.dat']))
    self.assertEqual(1, len(output['vm_stats-summary.dat']))
    self.assertEqual(1, len(output['new_graph_name-summary.dat']))

    self.assertEqual(
        {
            'traces': {
                'event_listeners': [[1, 492], [2, 490], [3, 487]],
                'event_listeners_max': [492, 0],
                'dom_nodes': [[1, 2621], [2, 2812], [3, 1242]],
                'dom_nodes_max': [2812, 0],
            },
            'units_x': 'iterations',
            'units': 'count',
            'rev': 12345,
        },
        json.loads(output['object_counts-summary.dat'][0]))

    self.assertEqual(
        {
            'traces': {
                'renderer_vm': [[1, 180.1], [2, 181.0], [3, 180.7]],
                'renderer_vm_max': [181, 0],
            },
            'units_x': 'iterations',
            'units': 'MB',
            'rev': 12345,
        },
        json.loads(output['vm_stats-summary.dat'][0]))

    self.assertEqual(
        {
            'traces': {
                'my_trace_name': [10, 0],
            },
            'units': 'kg',
            'units_x': '',
            'rev': 12345,
        },
        json.loads(output['new_graph_name-summary.dat'][0]))


if __name__ == '__main__':
  unittest.main()
