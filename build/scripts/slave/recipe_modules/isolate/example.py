# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'isolate',
  'json',
  'path',
  'step',
  'step_history',
]


def GenSteps(api):
  # Code coverage for isolate_server property.
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  assert api.isolate.isolate_server == 'https://isolateserver-dev.appspot.com'

  # That would read a list of files to search for, generated in GenTests.
  yield api.step('read test spec', ['cat'], stdout=api.json.output())
  expected_targets = api.step_history.last_step().stdout

  # Generates code coverage for find_isolated_tests corner cases.
  # TODO(vadimsh): This step doesn't actually make any sense when the recipe
  # is running for real via run_recipe.py.
  yield api.isolate.find_isolated_tests(api.path['build'], expected_targets)


def GenTests(api):
  def make_test(name, expected_targets, discovered_targets):
    return (
        api.test(name) +
        api.step_data(
            'read test spec', stdout=api.json.output(expected_targets)) +
        api.override_step_data(
            'find isolated tests', api.isolate.output_json(discovered_targets)))

  # Expected targets == found targets.
  yield make_test('basic', ['test1', 'test2'], ['test1', 'test2'])
  # No expectations, just discovering what's there returned by default mock.
  yield make_test('discover', None, None)
  # Found more than expected.
  yield make_test('extra', ['test1', 'test2'], ['test1', 'test2', 'extra_test'])
  # Didn't find something.
  yield make_test('missing', ['test1', 'test2'], ['test1'])
  # No expectations, and nothing has been found, produces warning.
  yield make_test('none', None, [])
