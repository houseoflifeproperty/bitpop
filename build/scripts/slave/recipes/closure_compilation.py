# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'properties',
  'step',
]


def GenSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('ninja')

  api.bot_update.ensure_checkout(force=True)

  api.step(
      'generate_gyp_files',
      [api.path['checkout'].join('build', 'gyp_chromium'),
       api.path['checkout'].join('third_party', 'closure_compiler',
                                 'compiled_resources.gyp')],
  )

  api.chromium.compile()


def GenTests(api):
  yield (
    api.test('main') +
    api.properties.generic(
      mastername='chromium.fyi',
      buildername='Closure Compilation Linux',
    )
  )
