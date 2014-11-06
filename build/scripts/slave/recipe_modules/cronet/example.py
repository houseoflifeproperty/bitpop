# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'cronet',
  'properties',
]

BUILDERS = {
  'local_test': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
    },
    'gyp_defs': {
      'use_goma': 0,
    }
  },
}

def GenSteps(api):
  buildername = api.properties['buildername']
  builder_config = BUILDERS.get(buildername, {})
  recipe_config = builder_config['recipe_config']
  kwargs = builder_config.get('kwargs', {})
  gyp_defs = builder_config.get('gyp_defs', {})

  cronet = api.cronet
  cronet.init_and_sync(recipe_config, kwargs, gyp_defs)
  cronet.build()
  cronet.upload_package(kwargs['BUILD_CONFIG'])
  cronet.run_tests()

def GenTests(api):
  bot_id = 'local_test'
  props = api.properties.generic(
    buildername=bot_id,
    revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
    repository='https://chromium.googlesource.com/chromium/src',
    branch='master',
    project='src',
  )
  yield api.test(bot_id) + props

