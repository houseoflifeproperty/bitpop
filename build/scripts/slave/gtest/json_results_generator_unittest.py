#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for json_results_generator.py.

 $ PYTHONPATH=../..:../../../third_party \
    python json_results_generator_unittest.py
"""

import unittest

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

  def _generate_and_test_full_results_json(self, passed_tests_list,
                                           failed_tests_list):
    tests_set = set(passed_tests_list) | set(failed_tests_list)

    get_test_set = lambda ts, label: set([t for t in ts if t.startswith(label)])
    DISABLED_tests = get_test_set(tests_set, 'DISABLED_')
    FLAKY_tests = get_test_set(tests_set, 'FLAKY_')
    MAYBE_tests = get_test_set(tests_set, 'MAYBE_')
    FAILS_tests = get_test_set(tests_set, 'FAILS_')
    PASS_tests = tests_set - (DISABLED_tests | FLAKY_tests | FAILS_tests |
        MAYBE_tests) - set(failed_tests_list)

    failed_tests = set(failed_tests_list) - DISABLED_tests

    test_timings = {}
    test_results_map = {}
    for i, test in enumerate(tests_set):
      test_name = canonical_name(test)
      test_timings[test_name] = i
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
      svn_revisions=[('blink', '12345')],
      file_writer=mock_writer)


    results_json = generator.get_full_results_json()
    self._verify_full_json_results(results_json, tests_set, PASS_tests,
                                   failed_tests, test_timings)
    self.assertEqual(results_json.get('blink_revision'), '12345')

  def test_get_full_results_json(self):
    self._generate_and_test_full_results_json(
        ['testPassed', 'FLAKY_testPassedAndFlaky', 'DISABLED_testDisabled02'],
        ['testFailed', 'DISABLED_testDisabled01', 'FLAKY_testFlakyAndFailed'])

    self._generate_and_test_full_results_json([], [])
    self._generate_and_test_full_results_json(['testPassed01', 'testPassed02'],
                                              [])
    self._generate_and_test_full_results_json(['DISABLED_testDisabled01'],
                                              ['FAILS_testFailed'])


  def _verify_full_json_results(self, results, all_tests, passed_tests,
                                failed_tests, test_timings):
    JRG = JSONResultsGenerator
    expected_passed = len(passed_tests)
    expected_failed = len(failed_tests)
    failure_summary = results[JRG.FAILURE_SUMMARY]
    self.assertEqual(expected_passed, failure_summary[JRG.PASS_LABEL])
    self.assertEqual(expected_failed, failure_summary[JRG.FAIL_LABEL])

    test_results = results[JRG.TESTS]
    for test_name, expected_time in test_timings.iteritems():
      actual_time = test_results[test_name][JRG.TEST_TIME]
      self.assertEqual(expected_time, actual_time)

    self.assertEqual(self.builder_name, results[JRG.BUILDER_NAME])
    self.assertEqual(self.build_number, results[JRG.BUILD_NUMBER])

    expected_tests_count = len(all_tests)
    self.assertEqual(expected_tests_count, len(test_results))


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
