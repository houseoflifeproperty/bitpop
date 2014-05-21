# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Parser and evaluator for performance tests.

Several performance tests have complicated log output, this module is intended
to help buildsteps parse these logs and identify if tests had anomalies.


"""

import json
import logging
import os
import re

from common import chromium_utils
import config

SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(6)

READABLE_FILE_PERMISSIONS = int('644', 8)
EXECUTABLE_FILE_PERMISSIONS = int('755', 8)

# For the GraphingLogProcessor, the file into which it will save a list
# of graph names for use by the JS doing the plotting.
GRAPH_LIST = config.Master.perf_graph_list

# perf_expectations.json holds performance expectations.  See
# http://dev.chromium.org/developers/testing/chromium-build-infrastructure/
# performance-test-plots/ for more info.
PERF_EXPECTATIONS_PATH = 'src/tools/perf_expectations/'

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


def JoinWithSpacesAndNewLine(array):
  return ' '.join(str(x) for x in array) + '\n'


class PerformanceLogProcessor(object):
  """Parent class for performance log parsers."""

  def __init__(self, revision=None, factory_properties=None,
               build_property=None, webkit_revision='undefined'):
    if factory_properties is None:
      factory_properties = {}
    self._matches = {}

    # Performance regression/speedup alerts.
    self._read_expectations = False
    self._perf_id = factory_properties.get('perf_id')
    self._perf_name = factory_properties.get('perf_name')
    self._perf_filename = factory_properties.get('perf_filename')
    self._test_name = factory_properties.get('test_name')
    self._perf_data = {}
    self._perf_test_keys = {}
    self._perf_ref_keys = {}
    self._perf_regress = []
    self._perf_improve = []

    self._output = {}
    self._finalized = False

    # The text summary will be built by other methods as we go.
    self._text_summary = []

    # Enable expectations if the local configuration supports it.
    self._expectations = (factory_properties.get('expectations')
                          and self._perf_id and self._perf_name)
    if self._expectations and not self._perf_filename:
      self._perf_filename = os.path.join(PERF_EXPECTATIONS_PATH,
                                         'perf_expectations.json')

    if revision:
      self._revision = revision
    else:
      self._revision = -1
    self._webkit_revision = webkit_revision

    if build_property:
      self._version = build_property.get('version') or 'undefined'
      self._channel = build_property.get('channel') or 'undefined'
    self._percentiles = [.1, .25, .5, .75, .90, .95, .99]

  def PerformanceLogs(self):
    if not self._finalized:
      self._FinalizeProcessing()
      self._finalized = True
    return self._output

  def PerformanceSummary(self):
    if not self._finalized:
      self._FinalizeProcessing()
      self._finalized = True
    return self.PerformanceChanges() + self._text_summary

  def _FinalizeProcessing(self):
    # to be overwritten by inheriting class
    pass

  def AppendLog(self, fn, data):
    self._output[fn] = self._output.get(fn, []) + data

  def PrependLog(self, fn, data):
    self._output[fn] = data + self._output.get(fn, [])

  def FailedTests(self):  # pylint: disable=R0201
    return []

  def SuppressionHashes(self):  # pylint: disable=R0201
    return []

  def ParsingErrors(self):  # pylint: disable=R0201
    return []

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
      m = re.search(r'^' + self._perf_name + '/' + self._test_name +
                   '/([\w\.-]+)/([\w\.-]+)$', perf_key)
      if not m:
        continue

      perf_data = all_perf_data[perf_key]
      graph = m.group(1)
      trace = m.group(2)

      # By default, all perf data is type=relative.
      perf_data.setdefault('type', 'relative')

      # By default, relative perf data is compare against the fqtn+'_ref'.
      if perf_data['type'] == 'relative' and 'ref' not in perf_data:
        perf_data['ref'] = '%s/%s/%s/%s_ref' % (
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
      logging.error('I/O Error reading expectations %s(%s): %s' %
                    (self._perf_filename, e.errno, e.strerror))
      return

    perf_data = {}
    if perf_file:
      try:
        perf_data = json.load(perf_file)
      except ValueError:
        perf_file.seek(0)
        logging.error('Error parsing expectations %s: \'%s\'' %
                      (self._perf_filename, perf_file.read().strip()))
      perf_file.close()

    # Find this perf/test entry
    if perf_data and perf_data.has_key('load') and perf_data['load']:
      self.LoadPerformanceExpectationsData(perf_data)
    else:
      logging.error('not loading perf expectations: perf_data is disabled')
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

    fqtn = '%s/%s/%s/%s' % (self._perf_name, self._test_name, graph, trace)
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
      text.append('MISS_EXPECTATIONS')

    if self._perf_regress:
      text.append('PERF_REGRESS: ' + ', '.join(self._perf_regress))

    if self._perf_improve:
      text.append('PERF_IMPROVE: ' + ', '.join(self._perf_improve))

    return text

  def ComparePerformance(self, graph, trace):
    # Skip graphs and traces we don't expect values for.
    if not graph in self._perf_data or not trace in self._perf_data[graph]:
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
      return WARNINGS

    # make sure regression and improvement logs are calculated
    self.PerformanceSummary()

    if self._perf_regress:
      return FAILURE

    if self._perf_improve:
      return WARNINGS

    # There was no change in performance, report success.
    return SUCCESS

  def ProcessLine(self, line):
    # overridden by superclass
    pass


class BenchpressLogProcessor(PerformanceLogProcessor):
  TIMING_REGEX = re.compile(r'.*Time \(([\w\d]+)\): (\d+)')

  def ProcessLine(self, log_line):
    if log_line.find('Time (') > -1:
      match = BenchpressLogProcessor.TIMING_REGEX.search(log_line)
      self._matches[match.group(1)] = int(match.group(2))

  def _FinalizeProcessing(self):
    algorithms = ['Fibonacci', 'Loop', 'Towers', 'Sieve', 'Permute', 'Queens',
                  'Recurse', 'Sum', 'BubbleSort', 'QuickSort', 'TreeSort',
                  'Tak', 'Takl']
    results = [self._revision]
    for algorithm in algorithms:
      results.append(self._matches[algorithm])

    self.AppendLog('summary.dat', [JoinWithSpacesAndNewLine(results)])

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

  def __init__(self, *args, **kwargs):
    PerformanceLogProcessor.__init__(self, *args, **kwargs)
    self.should_record = False
    self.summary_data = {}
    self.current_type_data = None

  def ProcessLine(self, line):
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

    line = line.strip()

    if line == PlaybackLogProcessor.LATEST_START_LINE:
      self.summary_data['latest'] = {}
      self.current_type_data = self.summary_data['latest']
    elif line == PlaybackLogProcessor.REFERENCE_START_LINE:
      self.summary_data['reference'] = {}
      self.current_type_data = self.summary_data['reference']

    if not self.should_record:
      if PlaybackLogProcessor.RESULTS_STARTING_LINE == line:
        self.should_record = True
      else:
        return
    else:
      if PlaybackLogProcessor.RESULTS_ENDING_LINE == line:
        self.should_record = False
        return

    if self.current_type_data is not None:
      match = PlaybackLogProcessor.RESULT_LINE.search(line)
      if match:
        test_name = match.group(1)
        test_data = int(match.group(2))

        if not self.current_type_data.get(test_name, {}):
          self.current_type_data[test_name] = {}

        if not self.current_type_data[test_name].get('data', []):
          self.current_type_data[test_name]['data'] = []

        self.current_type_data[test_name]['data'].append(test_data)

  def _FinalizeProcessing(self):
    # Only proceed if they both passed.
    if (self.summary_data.get('latest', {}) and
        self.summary_data.get('reference', {})):
      # Write the details file, which contains the raw results.
      filename = 'details.dat'
      data = json.dumps({self._revision: self.summary_data})
      self.AppendLog(filename, data)

      for summary in self.summary_data.itervalues():
        for test in summary.itervalues():
          mean, stdd = chromium_utils.MeanAndStandardDeviation(test['data'])
          test['mean'] = str(FormatFloat(mean))
          test['stdd'] = str(FormatFloat(stdd))
          # Remove test data as it is not needed in the summary file.
          del test['data']

      # Write the summary file, which contains the mean/stddev (data necessary
      # to draw the graphs).
      filename = 'summary.dat'
      self.AppendLog(filename, json.dumps({self._revision: self.summary_data}))


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


class EndureTrace(object):
  """Encapsulates the data needed for one trace on an endurance graph."""

  def __init__(self):
    self.values = []  # [(time, value), (time, value), ...]

  def __str__(self):
    return ', '.join(['(%s: %s)' % (pair[0], pair[1]) for pair in self.values])


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


class EndureGraph(object):
  """Encapsulates the data needed for one endurance performance graph."""

  def __init__(self):
    self.units = None
    self.traces = {}
    self.units_x = None
    self.stack = False
    self.stack_order = []

  def IsImportant(self):  # pylint: disable=R0201
    return False


class GraphingLogProcessor(PerformanceLogProcessor):
  """Parent class for any log processor expecting standard data to be graphed.

  The log will be parsed looking for any lines of the form
    <*>RESULT <graph_name>: <trace_name>= <value> <units>
  or
    <*>RESULT <graph_name>: <trace_name>= [<value>,value,value,...] <units>
  or
    <*>RESULT <graph_name>: <trace_name>= {<mean>, <std deviation>} <units>
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

  RESULTS_REGEX = re.compile(r'(?P<IMPORTANT>\*)?RESULT '
                             '(?P<GRAPH>[^:]*): (?P<TRACE>[^=]*)= '
                             '(?P<VALUE>[\{\[]?[-\d\., ]+[\}\]]?)('
                             ' ?(?P<UNITS>.+))?')
  HISTOGRAM_REGEX = re.compile(r'(?P<IMPORTANT>\*)?HISTOGRAM '
                               '(?P<GRAPH>[^:]*): (?P<TRACE>[^=]*)= '
                               '(?P<VALUE_JSON>{.*})(?P<UNITS>.+)?')

  def __init__(self, *args, **kwargs):
    PerformanceLogProcessor.__init__(self, *args, **kwargs)
    # A dict of Graph objects, by name.
    self._graphs = {}
    build_property = kwargs.get('build_property') or {}
    self._version = build_property.get('version') or 'undefined'
    self._channel = build_property.get('channel') or 'undefined'

    # Load performance expectations for this test.
    self.LoadPerformanceExpectations()

  def ProcessLine(self, line):
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
      trace.value, trace.stddev, filedata = self._CalculateStatistics(
          value_list, trace_name)
      for fn in filedata:
        self.PrependLog(fn, filedata[fn])
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
      histogram_data = json.loads(histogram_json)
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
    val, stddev = chromium_utils.FilteredMeanAndStandardDeviation(value_list)
    return val, stddev, {}

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
      AddTrace(name + '_ref')

    # Now append any other traces that have corresponding _ref traces, in
    # alphabetical order.
    keys = [x for x in graph.traces.keys() if x + '_ref' in remaining_traces]
    keys.sort()
    for name in keys:
      AddTrace(name)
      AddTrace(name + '_ref')

    # Finally, append any remaining traces, in alphabetical order.
    keys = remaining_traces.keys()
    keys.sort()
    traces.extend(keys)

    # Now build the JSON.
    trace_json = ', '.join(['"%s": ["%s", "%s"]' %
                            (x, graph.traces[x].value,
                             graph.traces[x].stddev) for x in traces])
    if not self._revision:
      raise Exception('revision is None')
    return ('{"traces": {%s}, "rev": "%s", "webkit_rev": "%s",'
            ' "ver": "%s", "chan": "%s"}'
            % (trace_json, self._revision, self._webkit_revision, self._version,
               self._channel))

  def _FinalizeProcessing(self):
    self.__CreateSummaryOutput()
    self.__GenerateGraphInfo()

  def __CreateSummaryOutput(self):
    """Write the summary data file and collect the waterfall display text.

    The summary file contains JSON-encoded data.

    The waterfall contains lines for each important trace, in the form
      tracename: value< (refvalue)>
    """

    for graph_name, graph in self._graphs.iteritems():
      # Write a line in the applicable summary file for each graph.
      filename = ('%s-summary.dat' % graph_name)
      data = [self.__BuildSummaryJSON(graph) + '\n']
      self._output[filename] = data + self._output.get(filename, [])

      # Add a line to the waterfall for each important trace.
      for trace_name, trace in graph.traces.iteritems():
        if trace_name.endswith('_ref'):
          continue
        if trace.important:
          display = '%s: %s' % (trace_name, FormatHumanReadable(trace.value))
          if graph.traces.get(trace_name + '_ref'):
            display += ' (%s)' % FormatHumanReadable(
                graph.traces[trace_name + '_ref'].value)
          self._text_summary.append(display)

    self._text_summary.sort()

  def __GenerateGraphInfo(self):
    """Output a list of graphs viewed this session, for use by the plotter.

    These will be collated and sorted on the master side.
    """
    graphs = {}
    for name, graph in self._graphs.iteritems():
      graphs[name] = {'name': name,
                      'important': graph.IsImportant(),
                      'units': graph.units}
    self._output[GRAPH_LIST] = json.dumps(graphs).split('\n')


class GraphingEndureLogProcessor(GraphingLogProcessor):
  """Handles additional processing for Chrome Endure data."""

  ENDURE_RESULTS_REGEX = re.compile(
      r'(?P<IMPORTANT>\*)?RESULT '
       '(?P<GRAPH>[^:]+): (?P<TRACE>[^=]+)= '
       '(?P<VALUE>\[[^\]]+\]) (?P<UNITSY>\S+) (?P<UNITSX>\S+)')

  ENDURE_VALUE_PAIR_REGEX = re.compile(
      r'\((?P<TIME>[0-9\.]+),(?P<VALUE>[0-9\.]+)\)')

  EVENT_RESULTS_REGEX = re.compile(
      r'(?P<IMPORTANT>\*)?RESULT '
       '_EVENT_: (?P<TRACE>[^=]+)= '
       '(?P<EVENT>\[[^\]]+\])')

  def ProcessLine(self, line):
    """Looks for Chrome Endure results: line to find the individual results."""
    # super() should be used instead of GetParentClass().
    # pylint: disable=W0212
    endure_match = self.ENDURE_RESULTS_REGEX.search(line)
    # TODO(dmikurube): Should handle EVENT lines.
    # event_match = self.EVENT_RESULTS_REGEX.search(line)
    if endure_match:
      self._ProcessEndureResultLine(endure_match)
    # elif event_match:
    #   self._ProcessEventLine(event_match)
    else:
      chromium_utils.GetParentClass(self).ProcessLine(self, line)

  def _ProcessEndureResultLine(self, line_match):
    match_dict = line_match.groupdict()
    graph_name = match_dict['GRAPH'].strip()
    trace_name = match_dict['TRACE'].strip()

    graph = self._graphs.get(graph_name, EndureGraph())
    graph.units = match_dict['UNITSY'] or ''
    graph.units_x = match_dict['UNITSX'] or ''
    # TODO(dmikurube): Should change the way to indicate stacking.
    if graph_name.endswith('-DMP'):
      graph.stack = True
      if not trace_name in graph.stack_order:
        graph.stack_order.append(trace_name)
    trace = graph.traces.get(trace_name, EndureTrace())
    trace_values_str = match_dict['VALUE']
    trace.important = match_dict['IMPORTANT'] or False

    if trace_values_str.startswith('[') and trace_values_str.endswith(']'):
      pair_list = re.findall(self.ENDURE_VALUE_PAIR_REGEX, trace_values_str)
      for match in pair_list:
        if match:
          trace.values.append([match[0], match[1]])
        else:
          logging.warning("Bad test output: '%s'" % trace_values_str)
          return
    else:
      logging.warning("Bad test output: '%s'" % trace_values_str)
      return

    graph.traces[trace_name] = trace
    self._graphs[graph_name] = graph

    # TODO(dmikurube): Write an original version to compare with extected data.
    # Store values in actual performance.
    # self.TrackActualPerformance(graph=graph_name, trace=trace_name,
    #                             value=trace.value, stddev=trace.stddev)

  def __BuildSummaryJSON(self, graph):
    """Sorts the traces and returns a summary JSON encoding of the graph.

    Although JS objects are not ordered, according to the spec, in practice
    everyone iterates in order, since not doing so is a compatibility problem.
    So we'll count on it here and produce an ordered list of traces.
    if stack_order is given in the graph, use the order.

    But since Python dicts are *not* ordered, we'll need to construct the JSON
    manually so we don't lose the trace order.
    """
    if graph.stack:
      trace_order = graph.stack_order
    else:
      trace_order = sorted(graph.traces.keys())

    # Now build the JSON.
    trace_json = ', '.join(
        ['"%s": [%s]' % (trace_name,
                         ', '.join(['["%s", "%s"]' % (pair[0], pair[1])
                                    for pair
                                    in graph.traces[trace_name].values]))
         for trace_name in trace_order])

    if not self._revision:
      raise Exception('revision is None')
    if graph.stack:
      stack_order = '[%s]' % ', '.join(
          ['"%s"' % name for name in graph.stack_order])
      return ('{"traces": {%s}, "rev": "%s", "stack": true, '
              '"stack_order": %s}'
              % (trace_json, self._revision, stack_order))
    else:
      return ('{"traces": {%s}, "rev": "%s", "stack": false}'
              % (trace_json, self._revision))

  def __CreateSummaryOutput(self):
    """Write the summary data file and collect the waterfall display text.

    The summary file contains JSON-encoded data.
    """

    for graph_name, graph in self._graphs.iteritems():
      # Write a line in the applicable summary file for each graph.
      filename = ('%s-summary.dat' % graph_name)
      data = [self.__BuildSummaryJSON(graph) + '\n']
      self._output[filename] = data + self._output.get(filename, [])

    self._text_summary.sort()

  def __GenerateGraphInfo(self):
    """Output a list of graphs viewed this session, for use by the plotter.

    These will be collated and sorted on the master side.
    """
    graphs = {}
    for name, graph in self._graphs.iteritems():
      # TODO(xusydoc): Write the annotator to be more general.
      graphs[name] = {'name': name,
                      'important': graph.IsImportant(),
                      'units': graph.units,
                      'units_x': graph.units_x}
    self._output[GRAPH_LIST] = json.dumps(graphs).split('\n')


class GraphingFrameRateLogProcessor(GraphingLogProcessor):
  """Handles additional processing for frame rate gesture data."""

  GESTURES_REGEXP = re.compile(r'^GESTURES '
                               '(?P<GRAPH>[^:]*): (?P<TRACE>[^=]*)= '
                               '\[(?P<GESTURES>.*)\] '
                               '\[(?P<MEANS>.*)\] '
                               '\[(?P<SIGMAS>.*)\]')

  def ProcessLine(self, line):
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
      if gestures:
        self.__SaveGestureData(graph_name, trace_name, gestures, means, sigmas)
    else:
      chromium_utils.GetParentClass(self).ProcessLine(self, line)

  def __SaveGestureData(self, graph_name, trace_name, gestures, means, sigmas):
    """Save a file holding the frame rate data for each gesture.

    Args:
      gestures: list of gesture names.
      means: list of mean values.
      sigmas: list of standard deviation values.
    """
    file_data = []
    for gesture, mean, sigma in zip(gestures, means, sigmas):
      file_data.append('%s (%s+/-%s)\n' % (gesture,
                                           FormatFloat(mean),
                                           FormatFloat(sigma)))

    filename = '%s_%s_%s.dat' % (self._revision, graph_name, trace_name)
    self.AppendLog(filename, file_data)


class GraphingPageCyclerLogProcessor(GraphingLogProcessor):
  """Handles additional processing for page-cycler timing data."""

  _page_list = ['(unknown)']
  PAGES_REGEXP = re.compile(r'^Pages: \[(?P<LIST>.*)\]')

  def ProcessLine(self, line):
    """Also looks for the Pages: line to find the page count."""
    # super() should be used instead of GetParentClass().
    # pylint: disable=W0212
    line_match = self.PAGES_REGEXP.search(line)
    if line_match:
      self._page_list = line_match.groupdict()['LIST'].strip().split(',')
      if len(self._page_list) < 1:
        self._page_list = ['(unknown)']
    else:
      chromium_utils.GetParentClass(self).ProcessLine(self, line)

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
    pagedata = self.__SavePageData(page_times, trace_name)
    val, stddev = chromium_utils.FilteredMeanAndStandardDeviation(sums)
    return val, stddev, pagedata

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
      file_data.append('%s (%s+/-%s): %s' % (page,
                                             FormatFloat(mean),
                                             FormatFloat(stddev),
                                             JoinWithSpacesAndNewLine(times)))

    filename = '%s_%s.dat' % (self._revision, trace_name)
    return {filename: file_data}
