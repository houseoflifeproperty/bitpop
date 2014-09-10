# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'filter',
  'json',
  'path',
  'properties',
  'raw_io',
  'step',
]

def GenSteps(api):
  api.path['checkout'] = api.path['slave_build']
  api.chromium.set_config('chromium')
  api.filter.does_patch_require_compile()
  assert (api.filter.result and api.properties['example_result']) or \
      (not api.filter.result and not api.properties['example_result'])
  assert (not api.properties['example_matching_exes'] or
          list(api.properties['example_matching_exes']) ==
          api.filter.matching_exes)
  api.step('hello', ['echo', 'Why hello, there.'])

def GenTests(api):
  # Trivial test with no exclusions and nothing matching.
  yield (api.test('basic') +
         api.properties(filter_exclusions=[]) +
         api.properties(example_result=None) +
         api.properties(example_matching_exes=None) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('yy')))
  
  # Matches exclusions
  yield (api.test('match_exclusion') +
         api.properties(filter_exclusions=['fo.*']) +
         api.properties(example_result=1) +
         api.properties(example_matching_exes=None) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('foo.cc')))

  # Doesnt match exclusion.
  yield (api.test('doesnt_match_exclusion') +
         api.properties(filter_exclusions=['fo.*']) +
         api.properties(example_result=None) +
         api.properties(example_matching_exes=None) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('bar.cc')))

  # Analyze returns matching result.
  yield (api.test('analyzes_returns_true') +
         api.properties(example_result=1) +
         api.properties(example_matching_exes=None) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                                  'targets': []})))

  # Analyze returns matching tests while matching all.
  yield (api.test('analyzes_matches_all_exes') +
         api.properties(matching_exes=['foo', 'bar']) +
         api.properties(example_matching_exes=['foo']) +
         api.properties(example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency (all)',
                                  'targets': ['foo']})))

  # Analyze matches all and returns matching tests.
  yield (api.test('analyzes_matches_exes') +
         api.properties(matching_exes=['foo', 'bar']) +
         api.properties(example_matching_exes=['foo']) +
         api.properties(example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                                  'targets': ['foo']})))

  # Analyze with error condition.
  yield (api.test('analyzes_error') +
         api.properties(matching_exes=None) +
         api.properties(example_matching_exes=None) +
         api.properties(example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'error': 'ERROR'})))

  # Analyze with python returning bad status.
  yield (api.test('bad_retcode_doesnt_fail') +
         api.properties(matching_exes=None) +
         api.properties(example_matching_exes=None) +
         api.properties(example_result=1) +
         api.step_data(
          'analyze',
          retcode=-1))
