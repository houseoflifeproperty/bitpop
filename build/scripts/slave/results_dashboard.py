#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for adding results to perf dashboard."""

import calendar
import datetime
import httplib
import json
import os
import urllib
import urllib2

from slave import slave_utils

# The paths in the results dashboard URLs for sending and viewing results.
SEND_RESULTS_PATH = '/add_point'
RESULTS_LINK_PATH = '/report?masters=%s&bots=%s&tests=%s&rev=%s'

# CACHE_DIR/CACHE_FILENAME will be created in options.build_dir to cache
# results which need to be retried.
CACHE_DIR = 'results_dashboard'
CACHE_FILENAME = 'results_to_retry'


def SendResults(data, url, build_dir):
  """Sends results to the Chrome Performance Dashboard.

  This function tries to send the given data to the dashboard, in addition to
  any data from the cache file. The cache file contains any data that wasn't
  successfully sent in a previous run.

  Args:
    data: The data to try to send. Must be JSON-serializable.
    url: Performance Dashboard URL (including schema).
    build_dir: Directory name, where the cache directory shall be.
  """
  results_json = json.dumps(data)

  # Write the new request line to the cache file, which contains all lines
  # that we shall try to send now.
  cache_file_name = _GetCacheFileName(build_dir)
  _AddLineToCacheFile(results_json, cache_file_name)

  # Send all the results from this run and the previous cache to the dashboard.
  fatal_error, errors = _SendResultsFromCache(cache_file_name, url)

  # Print out a Buildbot link annotation.
  link_annotation = _LinkAnnotation(url, data)
  if link_annotation:
    print link_annotation

  # Print any errors; if there was a fatal error, it should be an exception.
  for error in errors:
    print error
  if fatal_error:
    print 'Error uploading to dashboard.'
    print '@@@STEP_EXCEPTION@@@'


def _GetCacheFileName(build_dir):
  """Gets the cache filename, creating the file if it does not exist."""
  cache_dir = os.path.join(os.path.abspath(build_dir), CACHE_DIR)
  if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
  cache_filename = os.path.join(cache_dir, CACHE_FILENAME)
  if not os.path.exists(cache_filename):
    # Create the file.
    open(cache_filename, 'wb').close()
  return cache_filename


def _AddLineToCacheFile(line, cache_file_name):
  """Appends a line to the given file."""
  with open(cache_file_name, 'ab') as cache:
    cache.write('\n' + line)


def _SendResultsFromCache(cache_file_name, url):
  """Tries to send each line from the cache file in a separate request.

  This also writes data which failed to send back to the cache file.

  Args:
    cache_file_name: A file name.

  Returns:
    A pair (fatal_error, errors), where fatal_error is a boolean indicating
    whether there there was a major error and the step should fail, and errors
    is a list of error strings.
  """
  with open(cache_file_name, 'rb') as cache:
    cache_lines = cache.readlines()
  total_results = len(cache_lines)

  fatal_error = False
  errors = []

  lines_to_retry = []
  for index, line in enumerate(cache_lines):
    line = line.strip()
    if not line:
      continue
    print 'Sending result %d of %d to dashboard.' % (index + 1, total_results)

    # Check that the line that was read from the file is valid JSON. If not,
    # don't try to send it, and don't re-try it later; just print an error.
    if not _CanParseJSON(line):
      errors.append('Could not parse JSON: %s' % line)
      continue

    error = _SendResultsJson(url, line)

    # If the dashboard returned an error, we will re-try next time.
    if error:
      if 'HTTPError: 400 for JSON' in error:
        # This is a special case.  If the remote app rejects the json, its
        # probably malformed and we don't want to retry it.
        print 'Discarding JSON error: %s' % error
        break

      if index != len(cache_lines) - 1:
        # The very last item in the cache_lines list is the new results line.
        # If this line is not the new results line, then this results line
        # has already been tried before; now it's considered fatal.
        fatal_error = True

      # The lines to retry are all lines starting from the current one.
      lines_to_retry = [l.strip() for l in cache_lines[index:] if l.strip()]
      errors.append(error)
      break

  # Write any failing requests to the cache file.
  cache = open(cache_file_name, 'wb')
  cache.write('\n'.join(set(lines_to_retry)))
  cache.close()

  return fatal_error, errors


def _CanParseJSON(my_json):
  """Returns True if the input can be parsed as JSON, False otherwise."""
  try:
    json.loads(my_json)
  except ValueError:
    return False
  return True


def MakeListOfPoints(charts, bot, test_name, mastername, buildername,
                     buildnumber, supplemental_columns):
  """Constructs a list of point dictionaries to send.

  The format output by this function is the original format for sending data
  to the perf dashboard. Each

  Args:
    charts: A dictionary of chart names to chart data, as generated by the
        log processor classes (see process_log_utils.GraphingLogProcessor).
    bot: A string which comes from perf_id, e.g. linux-release.
    test_name: A test suite name, e.g. sunspider.
    mastername: Buildbot master name, e.g. chromium.perf.
    buildername: Builder name (for stdio links).
    buildnumber: Build number (for stdio links).
    supplemental_columns: A dictionary of extra data to send with a point.

  Returns:
    A list of dictionaries in the format accepted by the perf dashboard.
    Each dictionary has the keys "master", "bot", "test", "value", "revision".
    The full details of this format are described at http://goo.gl/TcJliv.
  """
  results = []

  # The master name used for the dashboard is the CamelCase name returned by
  # GetActiveMaster(), and not the canonical master name with dots.
  master = slave_utils.GetActiveMaster()

  for chart_name, chart_data in sorted(charts.items()):
    revision, revision_columns = _RevisionNumberColumns(chart_data, master)

    for trace_name, trace_values in sorted(chart_data['traces'].items()):
      is_important = trace_name in chart_data.get('important', [])
      test_path = _TestPath(test_name, chart_name, trace_name)
      result = {
          'master': master,
          'bot': bot,
          'test': test_path,
          'revision': revision,
          'masterid': mastername,
          'buildername': buildername,
          'buildnumber': buildnumber,
          'supplemental_columns': {}
      }

      # Add the supplemental_columns values that were passed in after the
      # calculated revision column values so that these can be overwritten.
      result['supplemental_columns'].update(revision_columns)
      result['supplemental_columns'].update(supplemental_columns)

      # Check whether this result is itself a time series (e.g. Endure result).
      # If so add the key "data", otherwise add "value" and "error".
      have_multi_value_data = False
      for value in trace_values:
        if isinstance(value, list):
          have_multi_value_data = True
      if have_multi_value_data:
        result['data'] = trace_values
      else:
        result['value'] = trace_values[0]
        result['error'] = trace_values[1]

      # Add other properties to this result dictionary if available.
      if chart_data.get('units'):
        result['units'] = chart_data['units']
      if chart_data.get('units_x'):
        result['units_x'] = chart_data['units_x']
      if chart_data.get('stack'):
        result['stack'] = chart_data['stack']
      if is_important:
        result['important'] = True

      results.append(result)

  return results


def _RevisionNumberColumns(data, master):
  """Get the revision number and revision-related columns from the given data.

  Args:
    data: A dict of information from one line of the log file.
    master: The name of the buildbot master.

  Returns:
    A pair with the revision number (which must be an int), and a dict of
    version-related supplemental columns.
  """
  def GetTimestamp():
    """Get the Unix timestamp for the current time."""
    return int(calendar.timegm(datetime.datetime.utcnow().utctimetuple()))

  revision_supplemental_columns = {}

  # The dashboard requires points' x-values to be integers, and points are
  # ordered by this. If the revision can't be parsed as an int, assume that
  # it's a git hash and use timestamp as the x-value.
  git_hash = None
  try:
    revision = int(data['rev'])
  except ValueError:
    # The dashboard requires ordered integer revision numbers. If the revision
    # is not an integer, assume it's a git hash and send a timestamp.
    revision = GetTimestamp()
    git_hash = data['rev']

  # Add Chromium version if it was specified, and use timestamp as x-value.
  if 'ver' in data and data['ver'] != 'undefined':
    revision_supplemental_columns['r_chrome_version'] = data['ver']
    revision_supplemental_columns['a_default_rev'] = 'r_chrome_version'
    revision = GetTimestamp()

  # Blink builds can have the same chromium revision for two builds. So
  # order them by timestamp to get them to show on the dashboard in the
  # order they were built.
  if master in ['ChromiumWebkit', 'Oilpan']:
    if not git_hash:
      revision_supplemental_columns['r_chromium_svn'] = revision
    revision = GetTimestamp()

  # Regardless of what the master is, if the given "rev" can't be parsed as
  # an int, we're assuming that it's a git hash.
  if git_hash:
    revision_supplemental_columns['r_chromium'] = git_hash

  # For Oilpan, send the webkit_rev as r_oilpan since we are getting
  # the oilpan branch revision instead of the Blink trunk revision
  # and set r_oilpan to be the dashboard default revision.
  if master == 'Oilpan':
    revision_supplemental_columns['r_oilpan'] = data['webkit_rev']
    revision_supplemental_columns['a_default_rev'] = 'r_oilpan'
  else:
    # For other revision data, add it if it's present and not undefined:
    for key in ['webkit_rev', 'webrtc_rev', 'v8_rev']:
      if key in data and data[key] != 'undefined':
        revision_supplemental_columns['r_' + key] = data[key]

  # If possible, also send the git hash.
  if 'git_revision' in data and data['git_revision'] != 'undefined':
    revision_supplemental_columns['r_chromium'] = data['git_revision']

  return revision, revision_supplemental_columns


def _TestPath(test_name, chart_name, trace_name):
  """Get the slash-separated test path to send.

  Args:
    test: Test name. Typically, this will be a top-level 'test suite' name.
    chart_name: Name of a chart where multiple trace lines are grouped. If the
        chart name is the same as the trace name, that signifies that this is
        the main trace for the chart.
    trace_name: The "trace name" is the name of an individual line on chart.

  Returns:
    A slash-separated list of names that corresponds to the hierarchy of test
    data in the Chrome Performance Dashboard; doesn't include master or bot
    name.
  """
  # For tests run on reference builds by builds/scripts/slave/telemetry.py,
  # "_ref" is appended to the trace name. On the dashboard, as long as the
  # result is on the right chart, it can just be called "ref".
  if trace_name == chart_name + '_ref':
    trace_name = 'ref'
  chart_name = chart_name.replace('_by_url', '')

  # No slashes are allowed in the trace name.
  trace_name = trace_name.replace('/', '_')

  # The results for "test/chart" and "test/chart/*" will all be shown on the
  # same chart by the dashboard. The result with path "test/path" is considered
  # the main trace for the chart.
  test_path = '%s/%s/%s' % (test_name, chart_name, trace_name)
  if chart_name == trace_name:
    test_path = '%s/%s' % (test_name, chart_name)
  return test_path


def _SendResultsJson(url, results_json):
  """Make a HTTP POST with the given JSON to the Performance Dashboard.

  Args:
    url: URL of Performance Dashboard instance, e.g.
        "https://chromeperf.appspot.com".
    results_json: JSON string that contains the data to be sent.

  Returns:
    None if successful, or an error string if there were errors.
  """
  # When data is provided to urllib2.Request, a POST is sent instead of GET.
  # The data must be in the application/x-www-form-urlencoded format.
  data = urllib.urlencode({'data': results_json})
  req = urllib2.Request(url + SEND_RESULTS_PATH, data)
  try:
    urllib2.urlopen(req)
  except urllib2.HTTPError, e:
    return 'HTTPError: %d for JSON %s\n' % (e.code, results_json)
  except urllib2.URLError, e:
    return 'URLError: %s for JSON %s\n' % (str(e.reason), results_json)
  except httplib.HTTPException, e:
    return 'HTTPException for JSON %s\n' % results_json
  return None


def _LinkAnnotation(url, data):
  """Prints a link annotation with a link to the dashboard if possible.

  Args:
    url: The Performance Dashboard URL, e.g. "https://chromeperf.appspot.com"
    data: The data that's being sent to the dashboard.

  Returns:
    An annotation to print, or None.
  """
  if not data or type(data) is not list:
    return None
  point = data[0]
  results_link = url + RESULTS_LINK_PATH % (
      urllib.quote(point['master']),
      urllib.quote(point['bot']),
      urllib.quote(point['test'].split('/')[0]),
      point['revision'])
  return '@@@STEP_LINK@%s@%s@@@' % ('Results Dashboard', results_link)
