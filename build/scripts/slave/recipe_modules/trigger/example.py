# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'properties',
    'trigger'
]


def GenSteps(api):
  api.trigger(*api.properties['trigger_props_list'])


def GenTests(api):
  yield (
      api.test('trigger_one_build') +
      api.properties(trigger_props_list=[{
          'buildername': 'cross-compiler',
          'a': 1,
        }])
      )

  yield (
      api.test('trigger_two_builds') +
      api.properties(trigger_props_list=[{
          'buildername': 'cross-compiler',
          'a': 1,
        }, {
          'buildername': 'cross-compiler',
          'a': 2,
        }])
      )
