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
  exes = api.m.properties.get('exes')
  compile_targets = api.m.properties.get('compile_targets')

  api.path['checkout'] = api.path['slave_build']
  api.chromium.set_config('chromium')
  api.filter.does_patch_require_compile(exes=exes,
                                        compile_targets=compile_targets,
                                        additional_name='chromium')

  assert (list(api.properties.get('example_changed_paths', ['foo.cc'])) == \
          api.filter.paths)
  assert (api.filter.result and api.properties['example_result']) or \
      (not api.filter.result and not api.properties['example_result'])
  assert (list(api.properties.get('example_matching_exes', [])) ==
          list(api.filter.matching_exes))
  assert (list(api.properties.get('example_matching_compile_targets', [])) ==
          api.filter.compile_targets)
  api.step('hello', ['echo', 'Why hello, there.'])

def GenTests(api):
  # Trivial test with no exclusions and nothing matching.
  yield (api.test('basic') +
         api.properties(
           filter_exclusions=[],
           example_changed_paths=['yy'],
           example_result=None) +
         api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
           'base': { 'exclusions': [] },
           'chromium': { 'exclusions': [] }})) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('yy')))

  # Matches exclusions
  yield (api.test('match_exclusion') +
         api.properties(example_result=1) +
         api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
           'base': { 'exclusions': ['fo.*'] },
           'chromium': { 'exclusions': [] }})) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('foo.cc')))

  # Matches exclusions in additional_name key
  yield (api.test('match_additional_name_exclusion') +
         api.properties(example_result=1) +
         api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
           'base': { 'exclusions': [] },
           'chromium': { 'exclusions': ['fo.*'] }})) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('foo.cc')))

  # Doesnt match exclusion.
  yield (api.test('doesnt_match_exclusion') +
         api.properties(
           example_changed_paths=['bar.cc'],
           example_result=None) +
         api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
           'base': { 'exclusions': ['fo.*'] },
           'chromium': { 'exclusions': [] }})) +
         api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('bar.cc')))

  # Analyze returns matching result.
  yield (api.test('analyzes_returns_true') +
         api.properties(example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                           'targets': [],
                           'build_targets': []})))

  # Analyze returns matching tests while matching all.
  yield (api.test('analyzes_matches_all_exes') +
         api.properties(example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency (all)'})))

  # Analyze matches all and returns matching tests.
  yield (api.test('analyzes_matches_exes') +
         api.properties(
           matching_exes=['foo', 'bar'],
           example_matching_exes=['foo'],
           example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                           'targets': ['foo'],
                           'build_targets': []})))

  # Analyze matches all and returns matching tests.
  yield (api.test('analyzes_matches_compile_targets') +
         api.properties(
           example_matching_exes=['foo'],
           example_matching_compile_targets=['bar'],
           example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                           'targets': ['foo'],
                           'build_targets': ['bar']})))

  # Analyze with error condition.
  yield (api.test('analyzes_error') +
         api.properties(
           matching_exes=[],
           example_result=1) +
         api.override_step_data(
          'analyze',
          api.json.output({'error': 'ERROR'})))

  # Analyze with python returning bad status.
  yield (api.test('bad_retcode_doesnt_fail') +
         api.properties(
           matching_exes=[],
           example_result=1) +
         api.step_data(
          'analyze',
          retcode=-1))
