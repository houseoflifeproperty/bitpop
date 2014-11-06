# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to test the deterministic build.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall
"""

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'json',
  'platform',
  'properties',
  'step',
]

DETERMINISTIC_BUILDERS = {
  'Android deterministic build': {
    'chromium_config': 'android',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'platform': 'linux',
  },
  'IOS deterministic build': {
    'chromium_config': 'chromium_ios_device',
    'gclient_config': 'ios',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_PLATFORM': 'ios',
      'TARGET_BITS': 32,
    },
    'platform': 'mac',
  },
  'Linux deterministic build': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
    'platform': 'linux',
  },
  'Mac deterministic build': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
    'platform': 'mac',
  },
  'Windows deterministic build': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
    'platform': 'win',
  },
}

def GenSteps(api):
  buildername = api.properties['buildername']
  recipe_config = DETERMINISTIC_BUILDERS[buildername]

  api.chromium.set_config(recipe_config['chromium_config'],
                          **recipe_config.get('chromium_config_kwargs',
                                              {'BUILD_CONFIG': 'Release'}))

  api.gclient.set_config(recipe_config['gclient_config'],
                         **recipe_config.get('gclient_config_kwargs', {}))
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  # Checkout chromium.
  api.bot_update.ensure_checkout(force=True)
  api.chromium.runhooks()

  api.chromium.compile(targets=['base_unittests'], force_clobber=True)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  mastername = 'chromium.swarm'
  for buildername in DETERMINISTIC_BUILDERS:
    test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                _sanitize_nonalpha(buildername))
    yield (
      api.test(test_name) +
      api.properties.scheduled() +
      api.properties.generic(buildername=buildername,
                             mastername=mastername) +
      api.platform(DETERMINISTIC_BUILDERS[buildername]['platform'], 32) +
      api.properties(configuration='Release')
    )
