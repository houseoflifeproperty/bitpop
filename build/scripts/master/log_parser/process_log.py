# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defines various log processors used by buildbot steps.

Current approach is to set an instance of log processor in
the ProcessLogTestStep implementation and it will call process()
method upon completion with full data from process stdio.
"""

import errno
import logging
import os
import re
import simplejson

import config
from common import chromium_utils

from buildbot.status import builder

READABLE_FILE_PERMISSIONS = int('644', 8)
EXECUTABLE_FILE_PERMISSIONS = int('755', 8)

# For the GraphingLogProcessor, the file into which it will save a list
# of graph names for use by the JS doing the plotting.
GRAPH_LIST = config.Master.perf_graph_list

# perf_expectations.json holds performance expectations.  See
# http://dev.chromium.org/developers/testing/chromium-build-infrastructure/performance-test-plots
# for more info.
PERF_EXPECTATIONS_PATH = '../../scripts/master/log_parser/perf_expectations/'

METRIC_SUFFIX = {-3: 'm', 0: '', 3: 'k', 6: 'M'}


def FormatFloat(number):
  """Formats float with two decimal points."""
  if number:
    return '%.2f' % number
  else:
    return '0.00'


def FormatPercentage(ratio):
  return '%s%%' % FormatFloat(100 * ratio)


def Divide(x, y):
  if y == 0:
    return float('inf')
  return float(x) / y


def FormatHumanReadable(number):
  """Formats a float into three significant figures, using metric suffixes.

  Only m, k, and M prefixes (for 1/1000, 1000, and 1,000,000) are used.
  Examples:
    0.0387    => 38.7m
    1.1234    => 1.12
    10866     => 10.8k
    682851200 => 683M
  """
  scientific = '%.2e' % float(number)     # 6.83e+005
  e_idx = scientific.find('e')            # 4, or 5 if negative
  digits = float(scientific[:e_idx])      # 6.83
  exponent = int(scientific[e_idx + 1:])  # int('+005') = 5
  while exponent % 3:
    digits *= 10
    exponent -= 1
  while exponent > 6:
    digits *= 10
    exponent -= 1
  while exponent < -3:
    digits /= 10
    exponent += 1
  if digits >= 100:
    # Don't append a meaningless '.0' to an integer number.
    digits = int(digits)
  # Exponent is now divisible by 3, between -3 and 6 inclusive: (-3, 0, 3, 6).
  return '%s%s' % (digits, METRIC_SUFFIX[exponent])


def Prepend(filename, data):
  chromium_utils.Prepend(filename, data)
  os.chmod(filename, READABLE_FILE_PERMISSIONS)


def JoinWithSpacesAndNewLine(array):
  return ' '.join(str(x) for x in array) + '\n'


class PerformanceLogProcessor(object):
  """ Parent class for performance log parsers. """

  def __init__(self, report_link=None, output_dir=None, factory_properties=None,
               perf_name=None, test_name=None, perf_filename=None):
    self._report_link = report_link
    if output_dir is None:
      output_dir = os.getcwd()
    elif output_dir.startswith('~'):
      output_dir = os.path.expanduser(output_dir)
    self._output_dir = output_dir
    factory_properties = factory_properties or {}
    self._matches = {}

    # Performance regression/speedup alerts.
    self._read_expectations = False
    self._perf_id = factory_properties.get('perf_id')
    self._perf_name = perf_name
    self._test_name = test_name
    self._perf_filename = perf_filename
    self._perf_data = {}
    self._perf_test_keys = {}
    self._perf_ref_keys = {}
    self._perf_regress = []
    self._perf_improve = []

    # Enable expectations if the local configuration supports it.
    self._expectations = (factory_properties.get('expectations')
                          and self._perf_id and self._perf_name)
    if self._expectations and not self._perf_filename:
      self._perf_filename = os.path.join(PERF_EXPECTATIONS_PATH,
                                         self._perf_id + ".json")

    # The revision isn't known until the Process() call.
    self._revision = -1

  def LoadPerformanceExpectationsData(self, all_perf_data):
    """Load the expectations data.

    All keys in perf_expectations have 4 components:
      slave/test/graph/trace

    LoadPerformanceExpectationsData finds all keys that match the initial
    portion of the string ("slave/test") and adds the graph and result
    portions to the expected performance structure.
    """

    for perf_key in all_perf_data.keys():
      # tools/perf_expectations/tests/perf_expectations_unittest.py should have
      # a matching regular expression.
      m = re.search(r"^" + self._perf_name + "/" + self._test_name +
                    "/([\w\.-]+)/([\w\.-]+)$", perf_key)
      if not m:
        continue

      perf_data = all_perf_data[perf_key]
      graph = m.group(1)
      trace = m.group(2)

      # By default, all perf data is type=relative.
      perf_data.setdefault('type', 'relative')

      # By default, relative perf data is compare against the fqtn+'_ref'.
      if perf_data['type'] == 'relative' and 'ref' not in perf_data:
        perf_data['ref'] = "%s/%s/%s/%s_ref" % (
            self._perf_name, self._test_name, graph, trace)

      # For each test key, we add a reference in _perf_test_keys to perf_data.
      self._perf_test_keys.setdefault(perf_key, [])
      self._perf_test_keys[perf_key].append(perf_data)

      # For each ref key, we add a reference in _perf_ref_keys to perf_data.
      if 'ref' in perf_data:
        self._perf_ref_keys.setdefault(perf_data['ref'], [])
        self._perf_ref_keys[perf_data['ref']].append(perf_data)

      self._perf_data.setdefault(graph, {})
      self._perf_data[graph][trace] = perf_data

  def LoadPerformanceExpectations(self):
    if not self._expectations:
      # self._expectations is false when a given factory doesn't enable
      # expectations, or doesn't have both perf_id and perf_name set.
      return
    try:
      perf_file = open(self._perf_filename, 'r')
    except IOError, e:
      logging.error("I/O Error reading expectations %s(%s): %s" %
                    (self._perf_filename, e.errno, e.strerror))
      return

    perf_data = {}
    if perf_file:
      try:
        perf_data = simplejson.load(perf_file)
      except ValueError:
        perf_file.seek(0)
        logging.error("Error parsing expectations %s: '%s'" %
                      (self._perf_filename, perf_file.read().strip()))
      perf_file.close()

    # Find this perf/test entry
    if perf_data and perf_data.has_key('load') and perf_data['load']:
      self.LoadPerformanceExpectationsData(perf_data)
    else:
      logging.error("not loading perf expectations: perf_data is disabled")
    self._read_expectations = True

  def TrackActualPerformance(self, graph=None, trace=None, value=None,
                             stddev=None):
    """Set actual performance data when we come across useful values.

    trace will be of the form "RESULTTYPE" or "RESULTTYPE_ref".
    A trace with _ref in its name refers to a reference build.

    Common result types for page cyclers: t, vm_rss_f_r, IO_b_b, etc.
    A test's result types vary between test types.  Currently, a test
    only needs to output the appropriate text format to embed a new
    result type.
    """

    fqtn = "%s/%s/%s/%s" % (self._perf_name, self._test_name, graph, trace)
    if fqtn in self._perf_test_keys:
      for perf_data in self._perf_test_keys[fqtn]:
        perf_data['actual_test'] = value
        perf_data['actual_var'] = stddev

        if perf_data['type'] == 'absolute' and 'actual_test' in perf_data:
          perf_data['actual_delta'] = perf_data['actual_test']

        elif perf_data['type'] == 'relative':
          if 'actual_test' in perf_data and 'actual_ref' in perf_data:
            perf_data['actual_delta'] = (
                perf_data['actual_test'] - perf_data['actual_ref'])

    if fqtn in self._perf_ref_keys:
      for perf_data in self._perf_ref_keys[fqtn]:
        perf_data['actual_ref'] = value

        if 'actual_test' in perf_data and 'actual_ref' in perf_data:
          perf_data['actual_delta'] = (
              perf_data['actual_test'] - perf_data['actual_ref'])

  def PerformanceChangesAsText(self):
    text = []

    if self._expectations and not self._read_expectations:
      text.append("MISS_EXPECTATIONS")

    if len(self._perf_regress) > 0:
      text.append("PERF_REGRESS: " + ', '.join(self._perf_regress))

    if len(self._perf_improve) > 0:
      text.append("PERF_IMPROVE: " + ', '.join(self._perf_improve))

    return text

  def ComparePerformance(self, graph, trace):
    # Skip graphs and traces we don't expect values for.
    if (not graph in self._perf_data or not trace in self._perf_data[graph]):
      return

    perfdata = self._perf_data[graph][trace]
    graph_result = graph + '/' + trace

    # Skip result types that didn't calculate a delta.
    if not 'actual_delta' in perfdata:
      return

    # Skip result types that don't have regress/improve values.
    if 'regress' not in perfdata or 'improve' not in perfdata:
      return

    # Set the high and low performance tests.
    # The actual delta needs to be within this range to keep the perf test
    # green.  If the results fall above or below this range, the test will go
    # red (signaling a regression) or orange (signaling a speedup).
    actual = perfdata['actual_delta']
    regress = perfdata['regress']
    improve = perfdata['improve']
    if (('better' in perfdata and perfdata['better'] == 'lower') or
        ('better' not in perfdata and regress > improve)):
      # The "lower is better" case.  (ie. time results)
      if actual < improve:
        ratio = 1 - Divide(actual, improve)
        self._perf_improve.append('%s (%s)' % (graph_result,
                                               FormatPercentage(ratio)))
      elif actual > regress:
        ratio = Divide(actual, regress) - 1
        self._perf_regress.append('%s (%s)' % (graph_result,
                                               FormatPercentage(ratio)))
    else:
      # The "higher is better" case.  (ie. score results)
      if actual > improve:
        ratio = Divide(actual, improve) - 1
        self._perf_improve.append('%s (%s)' % (graph_result,
                                               FormatPercentage(ratio)))
      elif actual < regress:
        ratio = 1 - Divide(actual, regress)
        self._perf_regress.append('%s (%s)' % (graph_result,
                                               FormatPercentage(ratio)))

  def PerformanceChanges(self):
    # Compare actual and expected results.
    for graph in self._perf_data:
      for trace in self._perf_data[graph]:
        self.ComparePerformance(graph, trace)

    return self.PerformanceChangesAsText()

  def evaluateCommand(self, cmd):
    if self._expectations and not self._read_expectations:
      return builder.WARNINGS

    if len(self._perf_regress) > 0:
      return builder.FAILURE

    if len(self._perf_improve) > 0:
      return builder.WARNINGS

    # There was no change in performance, report success.
    return builder.SUCCESS

  def Process(self, revision, data, build_property=None,
      webkit_revision='undefined'):
    """Invoked by the step with data from log file once it completes.

    Each subclass needs to override this method to provide custom logic,
    which should include setting self._revision.
    Args:
      revision: changeset revision number that triggered the build.
      data: content of the log file that needs to be processed.
      build_property: property for this build.

    Returns:
      A list of strings to be added to the waterfall display for this step.
    """
    self._revision = revision
    return []

  def ReportLink(self):
    return self._report_link

  def _ShouldWriteResults(self):
    """Tells whether the results should be persisted.

    Write results if revision number is available for the current build
    and the report link was specified.
    """
    return self._revision > 0 and self.ReportLink()

  def _MakeOutputDirectory(self):
    if self._output_dir and not os.path.exists(self._output_dir):
      os.makedirs(self._output_dir)


class BenchpressLogProcessor(PerformanceLogProcessor):
  TIMING_REGEX = re.compile(r'.*Time \(([\w\d]+)\): (\d+)')

  def __init__(self, *args, **kwargs):
    PerformanceLogProcessor.__init__(self, *args, **kwargs)
    # The text summary will be built by other methods as we go.
    self._text_summary = []

  def Process(self, revision, data, build_property=None,
      webkit_revision='undefined'):
    # Revision may be -1, for a forced build.
    self._revision = revision
    self._text_summary = []

    self._MakeOutputDirectory()
    for log_line in data.splitlines():
      self._ProcessLine(log_line)
    self._WriteResultsToSummaryFile()
    return self._text_summary

  def _ProcessLine(self, log_line):
    if log_line.find('Time (') > -1:
      match = BenchpressLogProcessor.TIMING_REGEX.search(log_line)
      self._matches[match.group(1)] = int(match.group(2))

  def _WriteResultsToSummaryFile(self):
    algorithms = ['Fibonacci', 'Loop', 'Towers', 'Sieve', 'Permute', 'Queens',
                   'Recurse', 'Sum', 'BubbleSort', 'QuickSort', 'TreeSort',
                   'Tak', 'Takl']
    results = [self._revision]
    for algorithm in algorithms:
      results.append(self._matches[algorithm])

    if self._ShouldWriteResults():
      filename = os.path.join(self._output_dir, 'summary.dat')
      Prepend(filename, JoinWithSpacesAndNewLine(results))

    # TODO(pamg): append an appropriate metric to the waterfall display if
    # we start running these tests again.
    # self._text_summary.append(...)


class PlaybackLogProcessor(PerformanceLogProcessor):
  """Log processor for playback results.

  Parses results and outputs results to file in JSON format.
  """

  LATEST_START_LINE = '=LATEST='
  REFERENCE_START_LINE = '=REFERENCE='

  RESULTS_STARTING_LINE = '<stats>'
  RESULTS_ENDING_LINE = '</stats>'

  # Matches stats counter output.  Examples:
  # c:WebFrameActiveCount: 3
  # t:WebFramePaintTime: 451
  # c:V8.OsMemoryAllocated: 3887400
  # t:V8.Parse: 159
  #
  # "c" is used to denote a counter, and "t" is used to denote a timer.
  RESULT_LINE = re.compile(r'^((?:c|t):[^:]+):\s*(\d+)')

  def Process(self, revision, data, build_property=None,
      webkit_revision='undefined'):
    """Does the actual log data processing.

    The data format follows this rule:
      {revision:
        {type:
          {testname:
            {
              'mean': test run mean time/count (only in summary.dat),
              'stdd': test run standard deviation (only in summary.dat),
              'data': raw test data for each run (only in details.dat)
            }
          }
        }
      }
    and written in one line by prepending to details.dat and summary.dat files
    in JSON format, where type is either "latest" or "reference".
    """

    # Revision may be -1, for a forced build.
    self._revision = revision

    self._MakeOutputDirectory()
    should_record = False
    summary_data = {}
    current_type_data = None
    for line in data.splitlines():
      line = line.strip()

      if line == PlaybackLogProcessor.LATEST_START_LINE:
        summary_data['latest'] = {}
        current_type_data = summary_data['latest']
      elif line == PlaybackLogProcessor.REFERENCE_START_LINE:
        summary_data['reference'] = {}
        current_type_data = summary_data['reference']

      if not should_record:
        if PlaybackLogProcessor.RESULTS_STARTING_LINE == line:
          should_record = True
        else:
          continue
      else:
        if PlaybackLogProcessor.RESULTS_ENDING_LINE == line:
          should_record = False
          continue

      if current_type_data != None:
        match = PlaybackLogProcessor.RESULT_LINE.search(line)
        if match:
          test_name = match.group(1)
          test_data = int(match.group(2))

          if current_type_data.get(test_name, {}) == {}:
            current_type_data[test_name] = {}

          if current_type_data[test_name].get('data', []) == []:
            current_type_data[test_name]['data'] = []

          current_type_data[test_name]['data'].append(test_data)

    # Only proceed if they both passed.
    if (summary_data.get('latest', {}) != {} and
        summary_data.get('reference', {}) != {}):
      # Write the details file, which contains the raw results.
      if self._ShouldWriteResults():
        filename = os.path.join(self._output_dir, 'details.dat')
        Prepend(filename, simplejson.dumps({revision : summary_data}) +
                                                '\n')

      for summary in summary_data.itervalues():
        for test in summary.itervalues():
          mean, stdd = chromium_utils.MeanAndStandardDeviation(test['data'])
          test['mean'] = str(FormatFloat(mean))
          test['stdd'] = str(FormatFloat(stdd))
          # Remove test data as it is not needed in the summary file.
          del test['data']

      # Write the summary file, which contains the mean/stddev (data necessary
      # to draw the graphs).
      if self._ShouldWriteResults():
        filename = os.path.join(self._output_dir, 'summary.dat')
        Prepend(filename, simplejson.dumps({revision : summary_data}) + '\n')
    return []


class Trace(object):
  """Encapsulates the data needed for one trace on a performance graph."""
  def __init__(self):
    self.important = False
    self.value = 0.0
    self.stddev = 0.0

  def __str__(self):
    result = FormatHumanReadable(self.value)
    if self.stddev:
      result += '+/-%s' % FormatHumanReadable(self.stddev)
    return result


class Graph(object):
  """Encapsulates the data needed for one performance graph."""
  def __init__(self):
    self.units = None
    self.traces = {}

  def IsImportant(self):
    """A graph is 'important' if any of its traces is."""
    for trace in self.traces.itervalues():
      if trace.important:
        return True
    return False


class GraphingLogProcessor(PerformanceLogProcessor):
  """Parent class for any log processor expecting standard data to be graphed.

  The log will be parsed looking for any lines of the form
    <*>RESULT <graph_name>: <trace_name>= <value> <units>
  or
    <*>RESULT <graph_name>: <trace_name>= [<value>,value,value,...] <units>
  or
    <*>RESULT <graph_name>: <trace_name>= {<mean>, <std deviation>} <units>
  or
    <*>HISTOGRAM <graph_name>: <trace_name>= histogram_JSON
  For example,
    *RESULT vm_final_browser: OneTab= 8488 kb
    RESULT startup: reference= [167.00,148.00,146.00,142.00] msec
  The leading * is optional; if it's present, the data from that line will be
  included in the waterfall display. If multiple values are given in [ ], their
  mean and (sample) standard deviation will be written; if only one value is
  given, that will be written. A trailing comma is permitted in the list of
  values.
  Any of the <fields> except <value> may be empty, in which case
  not-terribly-useful defaults will be used. The <graph_name> and <trace_name>
  should not contain any spaces, colons (:) nor equals-signs (=). Furthermore,
  the <trace_name> will be used on the waterfall display, so it should be kept
  short.  If the trace_name ends with '_ref', it will be interpreted as a
  reference value, and shown alongside the corresponding main value on the
  waterfall.
  """
  # _CalculateStatistics needs to be a member function.
  # pylint: disable=R0201

  RESULTS_REGEX = re.compile(
      r'(?P<IMPORTANT>\*)?RESULT '
       '(?P<GRAPH>[^:]*): (?P<TRACE>[^=]*)= '
       '(?P<VALUE>[\{\[]?[-\d\., ]+[\}\]]?)( ?(?P<UNITS>.+))?')
  HISTOGRAM_REGEX = re.compile(r'(?P<IMPORTANT>\*)?HISTOGRAM '
                               '(?P<GRAPH>[^:]*): (?P<TRACE>[^=]*)= '
                               '(?P<VALUE_JSON>{.*})(?P<UNITS>.+)?')

  def __init__(self, *args, **kwargs):
    PerformanceLogProcessor.__init__(self, *args, **kwargs)
    # The text summary will be built by other methods as we go.
    self._text_summary = []

    # A dict of Graph objects, by name.
    self._graphs = {}
    self._version = 'undefined'
    self._channel = 'undefined'
    self._webkit_revision = 'undefined'

    self._percentiles = [.1, .25, .5, .75, .90, .95, .99]

  def Process(self, revision, data, build_property=None,
      webkit_revision='undefined'):
    # Revision may be -1, for a forced build.
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._text_summary = []
    self._graphs = {}

    self._version = build_property.get('version') or 'undefined'
    self._channel = build_property.get('channel') or 'undefined'

    self._MakeOutputDirectory()

    # Load performance expectations for this test.
    self.LoadPerformanceExpectations()

    # Parse the log and fill _graphs.
    for log_line in data.splitlines():
      self._ProcessLine(log_line)

    self.__CreateSummaryOutput()
    if self._ShouldWriteResults():
      self.__SaveGraphInfo()
    return self.PerformanceChanges() + self._text_summary

  def _ProcessLine(self, line):
    results_match = self.RESULTS_REGEX.search(line)
    histogram_match = self.HISTOGRAM_REGEX.search(line)
    if results_match:
      self._ProcessResultLine(results_match)
    elif histogram_match:
      self._ProcessHistogramLine(histogram_match)

  def _ProcessResultLine(self, line_match):
    match_dict = line_match.groupdict()
    graph_name = match_dict['GRAPH'].strip()
    trace_name = match_dict['TRACE'].strip()

    graph = self._graphs.get(graph_name, Graph())
    graph.units = match_dict['UNITS'] or ''
    trace = graph.traces.get(trace_name, Trace())
    trace.value = match_dict['VALUE']
    trace.important = match_dict['IMPORTANT'] or False

    # Compute the mean and standard deviation for a multiple-valued item,
    # or the numerical value of a single-valued item.
    if trace.value.startswith('['):
      try:
        value_list = [float(x) for x in trace.value.strip('[],').split(',')]
      except ValueError:
        # Report, but ignore, corrupted data lines. (Lines that are so badly
        # broken that they don't even match the RESULTS_REGEX won't be
        # detected.)
        logging.warning("Bad test output: '%s'" % trace.value.strip())
        return
      trace.value, trace.stddev = self._CalculateStatistics(value_list,
                                                              trace_name)
    elif trace.value.startswith('{'):
      stripped = trace.value.strip('{},')
      try:
        trace.value, trace.stddev = [float(x) for x in stripped.split(',')]
      except ValueError:
        logging.warning("Bad test output: '%s'" % trace.value.strip())
        return
    else:
      try:
        trace.value = float(trace.value)
      except ValueError:
        logging.warning("Bad test output: '%s'" % trace.value.strip())
        return

    graph.traces[trace_name] = trace
    self._graphs[graph_name] = graph

    # Store values in actual performance.
    self.TrackActualPerformance(graph=graph_name, trace=trace_name,
                                value=trace.value, stddev=trace.stddev)

  def _ProcessHistogramLine(self, line_match):
    match_dict = line_match.groupdict()
    graph_name = match_dict['GRAPH'].strip()
    trace_name = match_dict['TRACE'].strip()
    histogram_json = match_dict['VALUE_JSON']
    important = match_dict['IMPORTANT'] or False
    try:
      histogram_data = simplejson.loads(histogram_json)
    except ValueError:
      # Report, but ignore, corrupted data lines. (Lines that are so badly
      # broken that they don't even match the HISTOGRAM_REGEX won't be
      # detected.)
      logging.warning("Bad test output: '%s'" % histogram_json.strip())
      return

    # Compute percentile data, create a graph for all percentile values.
    percentiles = self._CalculatePercentiles(histogram_data, trace_name)
    for i in percentiles:
      percentile_graph_name = graph_name + "_" + str(i['percentile'])
      graph = self._graphs.get(percentile_graph_name, Graph())
      graph.units = ''
      trace = graph.traces.get(percentile_graph_name, Trace())
      trace.value = i['value']
      trace.important = important
      graph.traces[percentile_graph_name] = trace
      self._graphs[percentile_graph_name] = graph
      self.TrackActualPerformance(graph=percentile_graph_name,
                                  trace=percentile_graph_name,
                                  value=i['value'])

    # Compute geometric mean and standard deviation.
    graph = self._graphs.get(graph_name, Graph())
    graph.units = ''
    trace = graph.traces.get(trace_name, Trace())
    trace.value, trace.stddev = self._CalculateHistogramStatistics(
        histogram_data, trace_name)
    trace.important = important
    graph.traces[trace_name] = trace
    self._graphs[graph_name] = graph
    self.TrackActualPerformance(graph=graph_name, trace=trace_name,
                                value=trace.value, stddev=trace.stddev)

  def _CalculateStatistics(self, value_list, trace_name):
    """Returns a tuple (mean, standard deviation) from a list of values.

    This method may be overridden by subclasses wanting a different standard
    deviation calcuation (or some other sort of error value entirely).

    Args:
      value_list: the list of values to use in the calculation
      trace_name: the trace that produced the data (not used in the base
          implementation, but subclasses may use it)
    """
    return chromium_utils.FilteredMeanAndStandardDeviation(value_list)

  def _CalculatePercentiles(self, histogram, trace_name):
    """Returns a list of percentile values from a histogram.

    Each value is a dictionary (relevant keys: "percentile" and "value").

    This method may be overridden by subclasses.

    Args:
      histogram: histogram data (relevant keys: "buckets", and for each bucket,
          "min", "max" and "count").
      trace_name: the trace that produced the data (not used in the base
          implementation, but subclasses may use it)
    """
    return chromium_utils.HistogramPercentiles(histogram, self._percentiles)

  def _CalculateHistogramStatistics(self, histogram, trace_name):
    """Returns the geometric mean and standard deviation for a histogram.

    This method may be overridden by subclasses.

    Args:
      histogram: histogram data (relevant keys: "buckets", and for each bucket,
          "min", "max" and "count").
      trace_name: the trace that produced the data (not used in the base
          implementation, but subclasses may use it)
    """
    geom_mean, stddev = chromium_utils.GeomMeanAndStdDevFromHistogram(
        histogram)
    return geom_mean, stddev

  def __BuildSummaryJSON(self, graph):
    """Sorts the traces and returns a summary JSON encoding of the graph.

    Although JS objects are not ordered, according to the spec, in practice
    everyone iterates in order, since not doing so is a compatibility problem.
    So we'll count on it here and produce an ordered list of traces.

    But since Python dicts are *not* ordered, we'll need to construct the JSON
    manually so we don't lose the trace order.
    """
    traces = []
    remaining_traces = graph.traces.copy()

    def AddTrace(trace_name):
      if trace_name in remaining_traces:
        traces.append(trace_name)
        del remaining_traces[trace_name]

    # First pull out any important traces in alphabetical order, and their
    # _ref traces even if not important.
    keys = [x for x in graph.traces.keys() if graph.traces[x].important]
    keys.sort()
    for name in keys:
      AddTrace(name)
      AddTrace(name + "_ref")

    # Now append any other traces that have corresponding _ref traces, in
    # alphabetical order.
    keys = [x for x in graph.traces.keys() if x + "_ref" in remaining_traces]
    keys.sort()
    for name in keys:
      AddTrace(name)
      AddTrace(name + "_ref")

    # Finally, append any remaining traces, in alphabetical order.
    keys = remaining_traces.keys()
    keys.sort()
    traces.extend(keys)

    # Now build the JSON.
    trace_json = ', '.join(['"%s": ["%s", "%s"]' %
        (x, graph.traces[x].value, graph.traces[x].stddev) for x in traces])
    if not self._revision:
      raise Exception("revision is None")
    return ('{"traces": {%s}, "rev": "%s", "webkit_rev": "%s",'
            ' "ver": "%s", "chan": "%s"}'
            % (trace_json, self._revision, self._webkit_revision, self._version,
                self._channel))

  def __CreateSummaryOutput(self):
    """Write the summary data file and collect the waterfall display text.

    The summary file contains JSON-encoded data.

    The waterfall contains lines for each important trace, in the form
      tracename: value< (refvalue)>
    """
    for graph_name, graph in self._graphs.iteritems():
      # Write a line in the applicable summary file for each graph.
      if  self._ShouldWriteResults():
        filename = os.path.join(self._output_dir,
                                "%s-summary.dat" % graph_name)
        Prepend(filename, self.__BuildSummaryJSON(graph) + "\n")

      # Add a line to the waterfall for each important trace.
      for trace_name, trace in graph.traces.iteritems():
        if trace_name.endswith("_ref"):
          continue
        if trace.important:
          display = "%s: %s" % (trace_name, FormatHumanReadable(trace.value))
          if graph.traces.get(trace_name + '_ref'):
            display += " (%s)" % FormatHumanReadable(
                                 graph.traces[trace_name + '_ref'].value)
          self._text_summary.append(display)

    self._text_summary.sort()

  def __SaveGraphInfo(self):
    """Keep a list of all graphs ever produced, for use by the plotter.

    Build a list of dictionaries:
      [{'name': graph_name, 'important': important, 'units': units},
       ...,
      ]
    sorted by importance (important graphs first) and then graph_name.
    Save this list into the GRAPH_LIST file for use by the plotting
    page. (We can't just use a plain dictionary with the names as keys,
    because dictionaries are inherently unordered.)
    """
    graph_filename = os.path.join(self._output_dir, GRAPH_LIST)
    try:
      graph_file = open(graph_filename)
    except IOError, e:
      if e.errno != errno.ENOENT:
        raise
      graph_file = None
    graph_list = []
    if graph_file:
      try:
        # We keep the original content of graphs.dat to avoid accidentally
        # removing graphs when a test encounters a failure.
        graph_list = simplejson.load(graph_file)
      except ValueError:
        graph_file.seek(0)
        logging.error("Error parsing %s: '%s'" % (GRAPH_LIST,
                      graph_file.read().strip()))
      graph_file.close()

    # We need the graph names from graph_list so we can skip graphs that already
    # exist in graph_list.
    graph_names = [x['name'] for x in graph_list]

    # Group all of the new graphs into their own list, ...
    new_graph_list = []
    for graph_name, graph in self._graphs.iteritems():
      if graph_name in graph_names:
        continue
      new_graph_list.append({'name': graph_name,
                             'important': graph.IsImportant(),
                             'units': graph.units})

    # sort them by not-'important', since True > False, and by graph_name, ...
    new_graph_list.sort(lambda x, y: cmp((not x['important'], x['name']),
                                         (not y['important'], y['name'])))

    # then add the new graph list to the main graph list.
    graph_list.extend(new_graph_list)

    # Write the resulting graph list.
    graph_file = open(graph_filename, 'w')
    simplejson.dump(graph_list, graph_file)
    graph_file.close()
    os.chmod(graph_filename, EXECUTABLE_FILE_PERMISSIONS)


class GraphingFrameRateLogProcessor(GraphingLogProcessor):
  """Handles additional processing for frame rate gesture data."""

  GESTURES_REGEXP = re.compile(
      r'^GESTURES '
       '(?P<GRAPH>[^:]*): (?P<TRACE>[^=]*)= '
       '\[(?P<GESTURES>.*)\] '
       '\[(?P<MEANS>.*)\] '
       '\[(?P<SIGMAS>.*)\]')

  def _ProcessLine(self, line):
    """Also looks for the Gestures: line to find the individual results."""
    # super() should be used instead of GetParentClass().
    # pylint: disable=W0212
    line_match = self.GESTURES_REGEXP.search(line)
    if line_match:
      match_dict = line_match.groupdict()
      graph_name = match_dict['GRAPH'].strip()
      trace_name = match_dict['TRACE'].strip()
      gestures = match_dict['GESTURES'].strip().split(',')
      means = [float(x) for x in match_dict['MEANS'].strip().split(',')]
      sigmas = [float(x) for x in match_dict['SIGMAS'].strip().split(',')]
      if len(gestures) > 0:
        self.__SaveGestureData(graph_name, trace_name, gestures, means, sigmas)
    else:
      chromium_utils.GetParentClass(self)._ProcessLine(self, line)

  def __SaveGestureData(self, graph_name, trace_name, gestures, means, sigmas):
    """Save a file holding the frame rate data for each gesture.

    Args:
      gestures: list of gesture names.
      means: list of mean values.
      sigmas: list of standard deviation values.
    """
    file_data = []
    for gesture, mean, sigma in zip(gestures, means, sigmas):
      file_data.append("%s (%s+/-%s)\n" % (gesture,
           FormatFloat(mean),
           FormatFloat(sigma)))

    filename = os.path.join(self._output_dir,
                            '%s_%s_%s.dat' % (self._revision,
                                              graph_name,
                                              trace_name))
    fileobj = open(filename, 'w')
    fileobj.write(''.join(file_data))
    fileobj.close()
    os.chmod(filename, READABLE_FILE_PERMISSIONS)


class GraphingPageCyclerLogProcessor(GraphingLogProcessor):
  """Handles additional processing for page-cycler timing data."""

  _page_list = ['(unknown)']
  PAGES_REGEXP = re.compile(r'^Pages: \[(?P<LIST>.*)\]')

  def _ProcessLine(self, line):
    """Also looks for the Pages: line to find the page count."""
    # super() should be used instead of GetParentClass().
    # pylint: disable=W0212
    line_match = self.PAGES_REGEXP.search(line)
    if line_match:
      self._page_list = line_match.groupdict()['LIST'].strip().split(',')
      if len(self._page_list) < 1:
        self._page_list = ['(unknown)']
    else:
      chromium_utils.GetParentClass(self)._ProcessLine(self, line)

  def _CalculateStatistics(self, value_list, trace_name):
    """Handles statistics generation and recording for page-cycler data.

    Sums the timings over all pages for each iteration and returns a tuple
    (mean, standard deviation) of those sums.  Also saves a data file
    <revision>_<tracename>.dat holding a line of times for each URL loaded,
    for use by humans when debugging a regression.
    """
    sums = []
    page_times = {}
    page_count = len(self._page_list)

    iteration_count = len(value_list) / page_count
    for iteration in range(iteration_count):
      start = page_count * iteration
      end = start + page_count
      iteration_times = value_list[start:end]
      sums += [sum(iteration_times)]
      for page_index in range(page_count):
        page = self._page_list[page_index]
        if page not in page_times:
          page_times[page] = []
        page_times[page].append(iteration_times[page_index])
    if self._ShouldWriteResults():
      self.__SavePageData(page_times, trace_name)
    return chromium_utils.FilteredMeanAndStandardDeviation(sums)

  def __SavePageData(self, page_times, trace_name):
    """Save a file holding the timing data for each page loaded.

    Args:
      page_times: a dict mapping a page URL to a list of its times
      trace_name: the trace that produced this set of times
    """
    file_data = []
    for page in self._page_list:
      times = page_times[page]
      mean, stddev = chromium_utils.FilteredMeanAndStandardDeviation(times)
      file_data.append("%s (%s+/-%s): %s" % (page,
           FormatFloat(mean),
           FormatFloat(stddev),
           JoinWithSpacesAndNewLine(times)))

    filename = os.path.join(self._output_dir,
                            '%s_%s.dat' % (self._revision, trace_name))
    fileobj = open(filename, 'w')
    fileobj.write(''.join(file_data))
    fileobj.close()
    os.chmod(filename, READABLE_FILE_PERMISSIONS)
