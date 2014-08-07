# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
  'step_history',
  'tryserver',
]


BUILDERS = {
  'chromium.webkit': {
    'builders': {
      'Android GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android', 'blink'],
      },
      'Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'gclient_apply_config': ['blink'],
      },
    },
  },
  'tryserver.blink': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android', 'blink'],
      },
      'linux_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'gclient_apply_config': ['blink'],
      },
    },
  },
  'chromium.linux': {
    'builders': {
      'Android GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Android GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
      },
      'Linux GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
      },
    },
  },
  'tryserver.chromium': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'android_chromium_gn_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'linux_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
      },
      'linux_chromium_gn_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
      },
    },
  },
  'client.v8': {
    'builders': {
      'V8 Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'gclient_apply_config': ['v8_bleeding_edge', 'show_v8_revision'],
        'set_custom_vars': [{'var': 'v8_revision',
                             'property': 'revision',
                             'default': 'HEAD'}]
      },
    },
  },
}

def GenSteps(api):
  # TODO: crbug.com/358481 . The build_config should probably be a property
  # passed in from slaves.cfg, but that doesn't exist today, so we need a
  # lookup mechanism to map bot name to build_config.
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)

  api.chromium.set_config('chromium',
                          **bot_config.get('chromium_config_kwargs', {}))

  # Note that we have to call gclient.set_config() and apply_config() *after*
  # calling chromium.set_config(), above, because otherwise the chromium
  # call would reset the gclient config to its defaults.
  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  # Overwrite custom deps variables based on build properties.
  # TODO: Figure out how to make this work generally for custom revisions.
  for custom in bot_config.get('set_custom_vars', []):
    s = api.gclient.c.solutions
    s[0].custom_vars[custom['var']] = api.properties.get(
        custom['property'], custom['default'])

  if api.tryserver.is_tryserver:
    api.step.auto_resolve_conflicts = True

  # FIXME(machenbach): Remove this as soon as crbug.com/380053 is resolved.
  if mastername == 'client.v8':
    yield api.gclient.checkout(abort_on_failure=True)
  else:
    yield api.bot_update.ensure_checkout(force=True)

  yield api.chromium.runhooks(run_gyp=False)

  yield api.chromium.run_gn()

  if api.tryserver.is_tryserver:
    yield api.chromium.compile(
        targets=['all'], abort_on_failure=False, can_fail_build=False)
    if api.step_history.last_step().retcode != 0:
      api.gclient.set_config('chromium_lkcr')

      yield api.bot_update.ensure_checkout(force=True, suffix='lkcr')
      yield api.chromium.runhooks(run_gyp=False)
      yield api.chromium.run_gn()
      yield api.chromium.compile(targets=['all'], force_clobber=True)
  else:
    yield api.chromium.compile(targets=['all'])

  # TODO(dpranke): crbug.com/353854. Run gn_unittests and other tests
  # when they are also being run as part of the try jobs.


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  # TODO: crbug.com/354674. Figure out where to put "simulation"
  # tests. We should have one test for each bot this recipe runs on.

  for mastername in BUILDERS:
    for buildername in BUILDERS[mastername]['builders']:
      test = (
          api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                   _sanitize_nonalpha(buildername))) +
          api.platform.name('linux')
      )
      if mastername.startswith('tryserver'):
        test += api.properties.tryserver(buildername=buildername,
                                         mastername=mastername)
      else:
        test += api.properties.generic(buildername=buildername,
                                       mastername=mastername)
      yield test

  yield (
    api.test('compile_failure') +
    api.platform.name('linux') +
    api.properties.tryserver(
        buildername='linux_chromium_gn_rel', mastername='tryserver.chromium') +
    api.step_data('compile', retcode=1)
  )
