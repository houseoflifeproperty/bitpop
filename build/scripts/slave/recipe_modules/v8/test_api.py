# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

from slave import recipe_test_api
from slave.recipe_modules.v8 import builders

class V8TestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = builders.BUILDERS

  def output_json(self, has_failures=False, wrong_results=False):
    if not has_failures:
      return self.m.json.output([{
        'arch': 'theArch',
        'mode': 'theMode',
        'results': [],
      }])
    if wrong_results:
      return self.m.json.output([{
        'arch': 'theArch1',
        'mode': 'theMode1',
        'results': [],
      },
      {
        'arch': 'theArch2',
        'mode': 'theMode2',
        'results': [],
      }])

    # Add enough failures to exceed the maximum number of shown failures
    # (test-name9 will be cut off).
    results = []
    for i in range(0, 10):
      results.append({
        'flags': ['--opt42'],
        'result': 'FAIL',
        'run': 1,
        'stdout': 'Some output.',
        'stderr': 'Some errput.',
        'name': 'suite-name/dir/test-name%d' % i,
        'command': 'out/theMode/d8 --opt42 test/suite-name/dir/test-name.js',
        'exit_code': 1,
      })
      results.append({
        'flags': ['--other'],
        'result': 'FAIL',
        'run': 1,
        'stdout': 'Some output.',
        'stderr': 'Some errput.',
        'name': 'suite-name/dir/test-name%d' % i,
        'command': 'out/theMode/d8 --other test/suite-name/dir/test-name.js',
        'exit_code': 1,
      })
      results.append({
        'flags': ['--other'],
        'result': 'CRASH',
        'run': 1,
        'stdout': 'Some output\nwith\nmore\nlines.',
        'stderr': 'Some errput.',
        'name': 'other-suite/dir/other-test-very-long-name%d' % i,
        'command': ('out/theMode/d8 --other '
                    'test/other-suite/dir/other-test-very-long-name.js'),
        'exit_code': 1,
      })

    return self.m.json.output([{
      'arch': 'theArch',
      'mode': 'theMode',
      'results': results,
    }])

  def perf_json(self, has_failures=False):
    result = {
      'errors': [],
      'traces':[
        {
          'units': 'score',
          'graphs': ['v8', 'Richards'],
          'results': ['30', '10', '20'],
        },
        {
          'units': 'ms',
          'graphs': ['v8', 'DeltaBlue'],
          'results': ['1.2', '1.2'],
        },
        {
          'units': 'score',
          'graphs': ['v8', 'Empty'],
          'results': [],
        },
      ],
    }
    if has_failures:
      result['errors'].extend(['Error line 1.', 'Error line 2.'])
    return self.m.json.output(result)

  @recipe_test_api.mod_test_data
  @staticmethod
  def test_failures(has_failures):
    return has_failures

  @recipe_test_api.mod_test_data
  @staticmethod
  def wrong_results(wrong_results):
    return wrong_results

  @recipe_test_api.mod_test_data
  @staticmethod
  def perf_failures(has_failures):
    return has_failures

  def __call__(self, test_failures=False, wrong_results=False,
               perf_failures=False):
    return (self.test_failures(test_failures) +
            self.wrong_results(wrong_results) +
            self.perf_failures(perf_failures))
