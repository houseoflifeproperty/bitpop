# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'raw_io',
  'swarming_client',
]

from slave import recipe_util

def GenSteps(api):
  # Code coverage for these methods.
  api.swarming_client.checkout('master')
  api.swarming_client.query_script_version('swarming.py')
  api.swarming_client.ensure_script_version('swarming.py', (0, 4, 4))

  # Coverage for |step_test_data| argument.
  api.swarming_client.query_script_version(
      'isolate.py', step_test_data=(0, 3, 1))

  # 'master' had swarming.py at v0.4.4 at the moment of writing this example.
  assert api.swarming_client.get_script_version('swarming.py') >= (0, 4, 4)

  # Coverage for 'fail' path of ensure_script_version.
  api.swarming_client.ensure_script_version('swarming.py', (0, 5, 0))

def GenTests(api):
  yield (
      api.test('basic') +
      api.step_data(
          'swarming.py --version',
          stdout=api.raw_io.output('0.4.4')))
