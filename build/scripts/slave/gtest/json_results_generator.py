# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A utility class to generate JSON results from given test results and upload
them to the specified results server.

"""

from __future__ import with_statement

import codecs
import logging
import os
import time
import urllib2

import simplejson
from slave.gtest.test_result import TestResult
from slave.gtest.test_results_uploader import TestResultsUploader

# A JSON results generator for generic tests.

JSON_PREFIX = 'ADD_RESULTS('
JSON_SUFFIX = ');'


def has_json_wrapper(string):
  return string.startswith(JSON_PREFIX) and string.endswith(JSON_SUFFIX)


def strip_json_wrapper(json_content):
  # FIXME: Kill this code once the server returns json instead of jsonp.
  if has_json_wrapper(json_content):
    return json_content[len(JSON_PREFIX):-len(JSON_SUFFIX)]
  return json_content


def convert_trie_to_flat_paths(trie, prefix=None):
  """Converts the directory structure in the given trie to flat paths,
  prepending a prefix to each."""
  result = {}
  for name, data in trie.iteritems():
    if prefix:
      name = prefix + '/' + name

    if len(data) and not 'results' in data:
      result.update(convert_trie_to_flat_paths(data, name))
    else:
      result[name] = data

  return result


def add_path_to_trie(path, value, trie):
  """Inserts a single flat directory path and associated value into a directory
  trie structure."""
  if not '/' in path:
    trie[path] = value
    return

  # we don't use slash
  # pylint: disable=W0612
  directory, slash, rest = path.partition('/')
  if not directory in trie:
    trie[directory] = {}
  add_path_to_trie(rest, value, trie[directory])


def generate_test_timings_trie(individual_test_timings):
  """Breaks a test name into chunks by directory and puts the test time as a
  value in the lowest part, e.g.
  foo/bar/baz.html: 1ms
  foo/bar/baz1.html: 3ms

  becomes
  foo: {
    bar: {
      baz.html: 1,
      baz1.html: 3
    }
  }
  """
  trie = {}
  for test_result in individual_test_timings:
    test = test_result.test_name

    add_path_to_trie(test, int(1000 * test_result.test_run_time), trie)

  return trie


class JSONResultsGenerator(object):
  """A JSON results generator for generic tests."""

  MAX_NUMBER_OF_BUILD_RESULTS_TO_LOG = 750
  # Min time (seconds) that will be added to the JSON.
  MIN_TIME = 1

  # Note that in non-chromium tests those chars are used to indicate
  # test modifiers (FAILS, FLAKY, etc) but not actual test results.
  PASS_RESULT = 'P'
  SKIP_RESULT = 'X'
  FAIL_RESULT = 'F'
  FLAKY_RESULT = 'L'
  NO_DATA_RESULT = 'N'

  MODIFIER_TO_CHAR = {
      TestResult.NONE: PASS_RESULT,
      TestResult.DISABLED: SKIP_RESULT,
      TestResult.FAILS: FAIL_RESULT,
      TestResult.FLAKY: FLAKY_RESULT}

  VERSION = 4
  VERSION_KEY = 'version'
  RESULTS = 'results'
  TIMES = 'times'
  BUILD_NUMBERS = 'buildNumbers'
  TIME = 'secondsSinceEpoch'
  TESTS = 'tests'

  FIXABLE_COUNT = 'fixableCount'
  FIXABLE = 'fixableCounts'
  ALL_FIXABLE_COUNT = 'allFixableCount'

  RESULTS_FILENAME = 'results.json'
  TIMES_MS_FILENAME = 'times_ms.json'
  INCREMENTAL_RESULTS_FILENAME = 'incremental_results.json'

  URL_FOR_TEST_LIST_JSON = \
    'http://%s/testfile?builder=%s&name=%s&testlistjson=1&testtype=%s&master=%s'

  def __init__(self, builder_name, build_name, build_number,
               results_file_base_path, builder_base_url,
               test_results_map, svn_revisions=None,
               test_results_server=None,
               test_type='',
               master_name='',
               file_writer=None):
    """Modifies the results.json file. Grabs it off the archive directory
    if it is not found locally.

    Args
      builder_name: the builder name (e.g. Webkit).
      build_name: the build name (e.g. webkit-rel).
      build_number: the build number.
      results_file_base_path: Absolute path to the directory containing the
        results json file.
      builder_base_url: the URL where we have the archived test results.
        If this is None no archived results will be retrieved.
      test_results_map: A dictionary that maps test_name to TestResult.
      svn_revisions: A (json_field_name, revision) pair for SVN
        repositories that tests rely on.  The SVN revision will be
        included in the JSON with the given json_field_name.
      test_results_server: server that hosts test results json.
      test_type: test type string (e.g. 'layout-tests').
      master_name: the name of the buildbot master.
      file_writer: if given the parameter is used to write JSON data to a file.
        The parameter must be the function that takes two arguments, 'file_path'
        and 'data' to be written into the file_path.
    """
    self._builder_name = builder_name
    self._build_name = build_name
    self._build_number = build_number
    self._builder_base_url = builder_base_url
    self._results_directory = results_file_base_path

    self._test_results_map = test_results_map
    self._test_results = test_results_map.values()

    self._svn_revisions = svn_revisions
    if not self._svn_revisions:
      self._svn_revisions = {}

    self._test_results_server = test_results_server
    self._test_type = test_type
    self._master_name = master_name
    self._file_writer = file_writer

  def generate_json_output(self):
    json = self.get_json()
    if json:
      file_path = os.path.join(self._results_directory,
                               self.INCREMENTAL_RESULTS_FILENAME)
      self._write_json(json, file_path)

  def generate_times_ms_file(self):
    times = generate_test_timings_trie(self._test_results_map.values())
    file_path = os.path.join(self._results_directory, self.TIMES_MS_FILENAME)
    self._write_json(times, file_path)

  def get_json(self):
    """Gets the results for the results.json file."""
    results_json = {}

    if not results_json:
      results_json, error = self._get_archived_json_results()
      if error:
        # If there was an error don't write a results.json
        # file at all as it would lose all the information on the
        # bot.
        logging.error('Archive directory is inaccessible. Not '
                      'modifying or clobbering the results.json '
                      'file: ' + str(error))
        return None

    builder_name = self._builder_name
    if results_json and builder_name not in results_json:
      logging.debug('Builder name (%s) is not in the results.json file.'
                    % builder_name)

    self._convert_json_to_current_version(results_json)

    if builder_name not in results_json:
      results_json[builder_name] = (
          self._create_results_for_builder_json())

    results_for_builder = results_json[builder_name]

    self._insert_generic_metadata(results_for_builder)

    self._insert_failure_summaries(results_for_builder)

    # Update the all failing tests with result type and time.
    tests = results_for_builder[self.TESTS]
    all_failing_tests = self._get_failed_test_names()
    all_failing_tests.update(convert_trie_to_flat_paths(tests))

    for test in all_failing_tests:
      self._insert_test_time_and_result(test, tests)

    return results_json

  def upload_json_files(self, json_files):
    """Uploads the given json_files to the test_results_server (if the
    test_results_server is given)."""
    if not self._test_results_server:
      return

    if not self._master_name:
      logging.error('--test-results-server was set, but --master-name was not. '
                    'Not uploading JSON files.')
      return

    print 'Uploading JSON files for builder: %s' % self._builder_name
    attrs = [('builder', self._builder_name),
             ('testtype', self._test_type),
             ('master', self._master_name)]

    files = [(f, os.path.join(self._results_directory, f)) for f in json_files]

    uploader = TestResultsUploader(self._test_results_server)
    # Set uploading timeout in case appengine server is having problem.
    # 120 seconds are more than enough to upload test results.
    uploader.upload(attrs, files, 120)

    print 'JSON files uploaded.'

  def _write_json(self, json_object, file_path):
    # Specify separators in order to get compact encoding.
    json_data = simplejson.dumps(json_object, separators=(',', ':'))
    json_string = json_data
    if self._file_writer:
      self._file_writer(file_path, json_string)
    else:
      with codecs.open(file_path, 'w', 'utf8') as f:
        f.write(json_string)

  def _get_test_timing(self, test_name):
    """Returns test timing data (elapsed time) in second
    for the given test_name."""
    if test_name in self._test_results_map:
      # Floor for now to get time in seconds.
      return int(self._test_results_map[test_name].test_run_time)
    return 0

  def _get_failed_test_names(self):
    """Returns a set of failed test names."""
    return set([r.test_name for r in self._test_results if r.failed])

  def _get_modifier_char(self, test_name):
    """Returns a single char (e.g. SKIP_RESULT, FAIL_RESULT,
    PASS_RESULT, NO_DATA_RESULT, etc) that indicates the test modifier
    for the given test_name.
    """
    if test_name not in self._test_results_map:
      return self.__class__.NO_DATA_RESULT

    test_result = self._test_results_map[test_name]
    if test_result.modifier in self.MODIFIER_TO_CHAR.keys():
      return self.MODIFIER_TO_CHAR[test_result.modifier]

    return self.__class__.PASS_RESULT

  def _get_result_char(self, test_name):
    """Returns a single char (e.g. SKIP_RESULT, FAIL_RESULT,
    PASS_RESULT, NO_DATA_RESULT, etc) that indicates the test result
    for the given test_name.
    """
    if test_name not in self._test_results_map:
      return self.__class__.NO_DATA_RESULT

    test_result = self._test_results_map[test_name]
    if test_result.modifier == TestResult.DISABLED:
      return self.__class__.SKIP_RESULT

    if test_result.failed:
      return self.__class__.FAIL_RESULT

    return self.__class__.PASS_RESULT

  def _get_archived_json_results(self):
    """Download JSON file that only contains test
    name list from test-results server. This is for generating incremental
    JSON so the file generated has info for tests that failed before but
    pass or are skipped from current run.

    Returns (archived_results, error) tuple where error is None if results
    were successfully read.
    """
    results_json = {}
    old_results = None
    error = None

    if not self._test_results_server:
      return {}, None

    results_file_url = (self.URL_FOR_TEST_LIST_JSON % (
        urllib2.quote(self._test_results_server),
        urllib2.quote(self._builder_name),
        self.RESULTS_FILENAME,
        urllib2.quote(self._test_type),
        urllib2.quote(self._master_name)))

    try:
      results_file = urllib2.urlopen(results_file_url)
      old_results = results_file.read()
    except urllib2.HTTPError, http_error:
      # A non-4xx status code means the bot is hosed for some reason
      # and we can't grab the results.json file off of it.
      if http_error.code < 400 and http_error.code >= 500:
        error = http_error
    except urllib2.URLError, url_error:
      error = url_error

    if old_results:
      # Strip the prefix and suffix so we can get the actual JSON object.
      old_results = strip_json_wrapper(old_results)

      try:
        results_json = simplejson.loads(old_results)
      except ValueError:
        logging.debug('results.json was not valid JSON. Clobbering.')
        # The JSON file is not valid JSON. Just clobber the results.
        results_json = {}
    else:
      logging.debug('Old JSON results do not exist. Starting fresh.')
      results_json = {}

    return results_json, error

  def _insert_failure_summaries(self, results_for_builder):
    """Inserts aggregate pass/failure statistics into the JSON.
    This method reads self._test_results and generates
    FIXABLE, FIXABLE_COUNT and ALL_FIXABLE_COUNT entries.

    Args:
      results_for_builder: Dictionary containing the test results for a
        single builder.
    """
    # Insert the number of tests that failed or skipped.
    fixable_count = len([r for r in self._test_results if r.fixable()])
    self._insert_item_into_raw_list(
        results_for_builder, fixable_count, self.FIXABLE_COUNT)

    # Create a test modifiers (FAILS, FLAKY etc) summary dictionary.
    entry = {}
    for test_name in self._test_results_map.iterkeys():
      result_char = self._get_modifier_char(test_name)
      entry[result_char] = entry.get(result_char, 0) + 1

    # Insert the pass/skip/failure summary dictionary.
    self._insert_item_into_raw_list(results_for_builder, entry, self.FIXABLE)

    # Insert the number of all the tests that are supposed to pass.
    all_test_count = len(self._test_results)
    self._insert_item_into_raw_list(results_for_builder,
                                    all_test_count, self.ALL_FIXABLE_COUNT)

  def _insert_item_into_raw_list(self, results_for_builder, item, key):
    """Inserts the item into the list with the given key in the results for
    this builder. Creates the list if no such list exists.

    Args:
      results_for_builder: Dictionary containing the test results for a
        single builder.
      item: Number or string to insert into the list.
      key: Key in results_for_builder for the list to insert into.
    """
    if key in results_for_builder:
      raw_list = results_for_builder[key]
    else:
      raw_list = []

    raw_list.insert(0, item)
    raw_list = raw_list[:self.MAX_NUMBER_OF_BUILD_RESULTS_TO_LOG]
    results_for_builder[key] = raw_list

  def _insert_item_run_length_encoded(self, item, encoded_results):
    """Inserts the item into the run-length encoded results.

    Args:
      item: String or number to insert.
      encoded_results: run-length encoded results. An array of arrays, e.g.
        [[3,'A'],[1,'Q']] encodes AAAQ.
    """
    if len(encoded_results) and item == encoded_results[0][1]:
      num_results = encoded_results[0][0]
      if num_results <= self.MAX_NUMBER_OF_BUILD_RESULTS_TO_LOG:
        encoded_results[0][0] = num_results + 1
    else:
      # Use a list instead of a class for the run-length encoding since
      # we want the serialized form to be concise.
      encoded_results.insert(0, [1, item])

  def _insert_generic_metadata(self, results_for_builder):
    """ Inserts generic metadata (such as version number, current time etc)
    into the JSON.

    Args:
      results_for_builder: Dictionary containing the test results for
        a single builder.
    """
    self._insert_item_into_raw_list(results_for_builder, self._build_number,
                                    self.BUILD_NUMBERS)

    # Include SVN revisions for the given repositories.
    for (name, revision) in self._svn_revisions:
      self._insert_item_into_raw_list(results_for_builder, revision,
                                      name + 'Revision')

    self._insert_item_into_raw_list(results_for_builder,
                                    int(time.time()),
                                    self.TIME)

  def _insert_test_time_and_result(self, test_name, tests):
    """ Insert a test item with its results to the given tests dictionary.

    Args:
      tests: Dictionary containing test result entries.
    """

    result = self._get_result_char(test_name)
    tm = self._get_test_timing(test_name)

    this_test = tests
    for segment in test_name.split('/'):
      if segment not in this_test:
        this_test[segment] = {}
      this_test = this_test[segment]

    if not len(this_test):
      self._populate_results_and_times_json(this_test)

    if self.RESULTS in this_test:
      self._insert_item_run_length_encoded(result, this_test[self.RESULTS])
    else:
      this_test[self.RESULTS] = [[1, result]]

    if self.TIMES in this_test:
      self._insert_item_run_length_encoded(tm, this_test[self.TIMES])
    else:
      this_test[self.TIMES] = [[1, tm]]

  def _convert_json_to_current_version(self, results_json):
    """If the JSON does not match the current version, converts it to the
    current version and adds in the new version number.
    """
    if self.VERSION_KEY in results_json:
      archive_version = results_json[self.VERSION_KEY]
      if archive_version == self.VERSION:
        return
    else:
      archive_version = 3

    # version 3->4
    if archive_version == 3:
      for results in results_json.itervalues():
        self._convert_tests_to_trie(results)

    results_json[self.VERSION_KEY] = self.VERSION

  def _convert_tests_to_trie(self, results):
    if not self.TESTS in results:
      return

    test_results = results[self.TESTS]
    test_results_trie = {}
    for test in test_results.iterkeys():
      single_test_result = test_results[test]
      add_path_to_trie(test, single_test_result, test_results_trie)

    results[self.TESTS] = test_results_trie

  def _populate_results_and_times_json(self, results_and_times):
    results_and_times[self.RESULTS] = []
    results_and_times[self.TIMES] = []
    return results_and_times

  def _create_results_for_builder_json(self):
    results_for_builder = {}
    results_for_builder[self.TESTS] = {}
    return results_for_builder
