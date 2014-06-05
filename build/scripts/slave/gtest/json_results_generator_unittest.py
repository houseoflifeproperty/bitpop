#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for json_results_generator.py.

 $ PYTHONPATH=../..:../../../third_party \
    python json_results_generator_unittest.py
"""

import unittest

from slave.gtest import json_results_generator
from slave.gtest.json_results_generator import generate_test_timings_trie
from slave.gtest.json_results_generator import JSONResultsGenerator
from slave.gtest.test_result import TestResult
from slave.gtest.test_result import canonical_name
import simplejson


class JSONGeneratorTest(unittest.TestCase):
  def setUp(self):
    self.builder_name = 'DUMMY_BUILDER_NAME'
    self.build_name = 'DUMMY_BUILD_NAME'
    self.build_number = 'DUMMY_BUILDER_NUMBER'

    # For archived results.
    self._json = None
    self._num_runs = 0
    self._tests_set = set([])
    self._test_timings = {}
    self._failed_count_map = {}

    self._PASS_count = 0
    self._DISABLED_count = 0
    self._FLAKY_count = 0
    self._FAILS_count = 0
    self._fixable_count = 0

  def test_strip_json_wrapper(self):
    json = "['contents']"
    self.assertEqual(json_results_generator.strip_json_wrapper(
        json_results_generator.JSON_PREFIX + json +
        json_results_generator.JSON_SUFFIX),
        json)
    self.assertEqual(json_results_generator.strip_json_wrapper(json), json)

  def _test_json_generation(self, passed_tests_list, failed_tests_list, expected_test_list=None):
    tests_set = set(passed_tests_list) | set(failed_tests_list)

    get_test_set = lambda ts, label: set([t for t in ts if t.startswith(label)])
    DISABLED_tests = get_test_set(tests_set, 'DISABLED_')
    FLAKY_tests = get_test_set(tests_set, 'FLAKY_')
    MAYBE_tests = get_test_set(tests_set, 'MAYBE_')
    FAILS_tests = get_test_set(tests_set, 'FAILS_')
    PASS_tests = tests_set - (DISABLED_tests | FLAKY_tests | FAILS_tests |
        MAYBE_tests)

    failed_tests = set(failed_tests_list) - DISABLED_tests
    failed_count_map = dict([(t, 1) for t in failed_tests])

    test_timings = {}
    i = 0

    test_results_map = dict()
    for test in tests_set:
      test_name = canonical_name(test)
      test_timings[test_name] = float(self._num_runs * 100 + i)
      i += 1
      test_results_map[test_name] = TestResult(test,
        failed=(test in failed_tests),
        elapsed_time=test_timings[test_name])

    # Do not write to an actual file.
    mock_writer = lambda path, data: True

    generator = JSONResultsGenerator(
      self.builder_name, self.build_name, self.build_number,
      '',
      None,   # don't fetch past json results archive
      test_results_map,
      svn_revisions=[('blink', '.')],
      file_writer=mock_writer)

    failed_count_map = dict([(t, 1) for t in failed_tests])

    # Test incremental json results
    incremental_json = generator.get_json()
    self._verify_json_results(
        tests_set,
        test_timings,
        failed_count_map,
        len(PASS_tests),
        len(DISABLED_tests),
        len(FLAKY_tests),
        len(DISABLED_tests | failed_tests),
        incremental_json,
        1,
        expected_test_list)

    # We don't verify the results here, but at least we make sure the code
    # runs without errors.
    generator.generate_json_output()
    generator.generate_times_ms_file()

  def _verify_json_results(self, tests_set, test_timings, failed_count_map,
                           PASS_count, DISABLED_count, FLAKY_count,
                           fixable_count,
                           json, num_runs, expected_test_list):
    # Aliasing to a short name for better access to its constants.
    JRG = JSONResultsGenerator

    self.assertTrue(JRG.VERSION_KEY in json)
    self.assertTrue(self.builder_name in json)

    buildinfo = json[self.builder_name]
    self.assertTrue(JRG.FIXABLE in buildinfo)
    self.assertTrue(JRG.TESTS in buildinfo)
    self.assertEqual(len(buildinfo[JRG.BUILD_NUMBERS]), num_runs)
    self.assertEqual(buildinfo[JRG.BUILD_NUMBERS][0], self.build_number)

    if tests_set or DISABLED_count:
      fixable = {JRG.PASS_RESULT:0, JRG.SKIP_RESULT:0, JRG.FLAKY_RESULT:0}
      for fixable_items in buildinfo[JRG.FIXABLE]:
        for (test_type, count) in fixable_items.iteritems():
          if test_type in fixable:
            fixable[test_type] = fixable[test_type] + count
          else:
            fixable[test_type] = count

      self.assertEqual(fixable[JRG.PASS_RESULT], PASS_count)
      self.assertEqual(fixable[JRG.SKIP_RESULT], DISABLED_count)
      self.assertEqual(fixable[JRG.FLAKY_RESULT], FLAKY_count)

    if failed_count_map:
      tests = buildinfo[JRG.TESTS]
      for test_name in failed_count_map.iterkeys():
        canonical = canonical_name(test_name)
        if expected_test_list:
          self.assertTrue(canonical in expected_test_list)
        test = self._find_test_in_trie(canonical, tests)

        failed = 0
        for result in test[JRG.RESULTS]:
          if result[1] == JRG.FAIL_RESULT:
            failed += result[0]
        self.assertEqual(failed_count_map[test_name], failed)

        timing_count = 0
        for timings in test[JRG.TIMES]:
          if timings[1] == test_timings[canonical]:
            timing_count = timings[0]
        self.assertEqual(1, timing_count)

    if fixable_count:
      self.assertEqual(sum(buildinfo[JRG.FIXABLE_COUNT]), fixable_count)

  def _find_test_in_trie(self, path, trie):
    nodes = path.split("/")
    sub_trie = trie
    for node in nodes:
      self.assertTrue(node in sub_trie)
      sub_trie = sub_trie[node]
    return sub_trie

  def test_json_generation(self):
    self._test_json_generation([], [])
    self._test_json_generation(['A1', 'B1'], [])
    self._test_json_generation([], ['FAILS_A2', 'FAILS_B2'])
    self._test_json_generation(['DISABLED_A3', 'DISABLED_B3'], [])
    self._test_json_generation(['A4'], ['B4', 'FAILS_C4'])
    self._test_json_generation(['DISABLED_C5', 'DISABLED_D5'], ['A5', 'B5'])
    self._test_json_generation(
      ['A6', 'B6', 'FAILS_C6', 'DISABLED_E6', 'DISABLED_F6'],
      ['FAILS_D6'])

    # Generate JSON with the same test sets. (Both incremental results and
    # archived results must be updated appropriately.)
    self._test_json_generation(
      ['A', 'FLAKY_B', 'DISABLED_C'],
      ['FAILS_D', 'FLAKY_E'],
      ['D', 'E'])
    self._test_json_generation(
      ['A', 'DISABLED_C', 'FLAKY_E'],
      ['FLAKY_B', 'FAILS_D'])
    self._test_json_generation(
      ['FLAKY_B', 'DISABLED_C', 'FAILS_D'],
      ['A', 'FLAKY_E'])

  def test_hierarchical_json_generation(self):
    # FIXME: Re-work tests to be more comprehensible and comprehensive.
    self._test_json_generation(['foo/A'], ['foo/B', 'bar/C'])

  def test_test_timings_trie(self):
    individual_test_timings = []
    individual_test_timings.append(
        TestResult('foo/bar/baz.html', failed=False, elapsed_time=1.2))
    individual_test_timings.append(
        TestResult('bar.html', failed=False, elapsed_time=0.0001))
    trie = generate_test_timings_trie(individual_test_timings)

    expected_trie = {
      'bar.html': 0,
      'foo': {
        'bar': {
          'baz.html': 1200,
        }
      }
    }

    self.assertEqual(simplejson.dumps(trie), simplejson.dumps(expected_trie))


if __name__ == '__main__':
  unittest.main()
