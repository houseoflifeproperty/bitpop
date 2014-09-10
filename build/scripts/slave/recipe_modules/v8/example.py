# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'perf_dashboard',
  'properties',
  'v8',
]


def GenSteps(api):
  # Minimalistic example for running the performance tests.
  api.v8.set_config('v8')
  api.v8.set_bot_config({'perf': ['example1', 'example2']})
  api.perf_dashboard.set_config('testing')
  api.v8.checkout()
  perf_config = {
    'example1': {
      'name': 'Example1',
      'json': 'example1.json',
    },
    'example2': {
      'name': 'Example2',
      'json': 'example2.json',
    }
  }
  api.v8.runperf(api.v8.perf_tests, perf_config, category='ia32')


def GenTests(api):
  yield (
    api.test('perf_failures') +
    api.v8(perf_failures=True) +
    api.step_data('Example1', retcode=1) +
    api.properties.generic(mastername='Fake_Master',
                           buildername='Fake Builder',
                           revision='20123')
  )
  yield (
    api.test('forced_build') +
    api.properties.generic(mastername='Fake_Master',
                           buildername='Fake Builder')
  )
