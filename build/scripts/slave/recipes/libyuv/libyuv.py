# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for Libyuv stand-alone.

DEPS = [
  'chromium',
  'gclient',
  'libyuv',
  'path',
  'platform',
  'properties',
  'step',
  'tryserver',
]

RECIPE_CONFIGS = {
  'libyuv': {
    'chromium_config': 'libyuv',
    'gclient_config': 'libyuv',
  },
  'libyuv_clang': {
    'chromium_config': 'libyuv_clang',
    'gclient_config': 'libyuv',
  },
  'libyuv_asan': {
    'chromium_config': 'libyuv_asan',
    'gclient_config': 'libyuv',
  },
  'libyuv_android': {
    'chromium_config': 'libyuv_android',
    'gclient_config': 'libyuv_android',
  },
  'libyuv_android_clang': {
    'chromium_config': 'libyuv_android_clang',
    'gclient_config': 'libyuv_android',
  },
  'libyuv_ios': {
    'chromium_config': 'libyuv_ios',
    'gclient_config': 'libyuv_ios',
  },
}

BUILDERS = {
  'client.libyuv': {
    'builders': {
      'Win32 Debug (VS2010)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2010'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'Win32 Release (VS2010)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2010'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'Win64 Debug (VS2010)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2010'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'Win64 Release (VS2010)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2010'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'Win32 Debug (VS2012)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2012'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'Win32 Release (VS2012)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2012'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'Win64 Debug (VS2012)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2012'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'Win64 Release (VS2012)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2012'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'Win32 Debug (VS2013)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2013'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'Win32 Release (VS2013)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2013'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'Win64 Debug (VS2013)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2013'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'Win64 Release (VS2013)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['msvs2013'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'Mac32 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'mac'},
      },
      'Mac32 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'mac'},
      },
      'Mac64 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'mac'},
      },
      'Mac64 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'mac'},
      },
      'Mac Asan': {
        'recipe_config': 'libyuv_asan',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'mac'},
      },
      'iOS Debug': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'testing': {'platform': 'mac'},
      },
      'iOS Release': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'testing': {'platform': 'mac'},
      },
      'Linux32 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux32 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux64 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux64 Debug (GN)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release (GN)': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux Asan': {
        'recipe_config': 'libyuv_asan',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux Memcheck': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['libyuv_valgrind'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Linux Tsan v2': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['tsan2'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Android Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'Android Release': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'Android ARM64 Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'Android Clang Debug': {
        'recipe_config': 'libyuv_android_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'Android GN': {
        'recipe_config': 'libyuv_android',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'Android GN (dbg)': {
        'recipe_config': 'libyuv_android',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.libyuv': {
    'builders': {
      'win': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'win_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'win'},
      },
      'win_x64_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'win'},
      },
      'mac': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'mac'},
      },
      'mac_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'mac'},
      },
      'mac_x64_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'mac'},
      },
      'mac_asan': {
        'recipe_config': 'libyuv_asan',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'mac'},
      },
      'ios': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'testing': {'platform': 'mac'},
      },
      'ios_rel': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'testing': {'platform': 'mac'},
      },
      'linux': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'linux_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'linux_gn': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'linux_gn_rel': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'linux_asan': {
        'recipe_config': 'libyuv_asan',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'linux_memcheck': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['libyuv_valgrind'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'linux_tsan2': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['tsan2'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'android': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'android_rel': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'android_clang': {
        'recipe_config': 'libyuv_android_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'android_arm64': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
      'android_gn': {
        'recipe_config': 'libyuv_android',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'android_gn_rel': {
        'recipe_config': 'libyuv_android',
        'chromium_apply_config': ['gn'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
    },
  },
}

def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                      (buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  recipe_config = RECIPE_CONFIGS.get(recipe_config_name)
  assert recipe_config, ('Cannot find recipe_config "%s" for builder "%r".' %
                         (recipe_config_name, buildername))

  api.chromium.set_config(recipe_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  api.gclient.set_config(recipe_config['gclient_config'])
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')

  # TODO(kjellander): Convert to use bot_update instead.
  api.gclient.checkout()
  api.tryserver.maybe_apply_issue()
  api.chromium.runhooks()

  if api.chromium.c.project_generator.tool == 'gn':
    api.chromium.run_gn(use_goma=True)
    api.chromium.compile(targets=['all'])
  else:
    api.chromium.compile()

  if api.chromium.c.TARGET_PLATFORM in ('win', 'mac', 'linux'):
    api.chromium.runtest('libyuv_unittest')


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  def generate_builder(mastername, buildername, revision, suffix=None):
    suffix = suffix or ''
    bot_config = BUILDERS[mastername]['builders'][buildername]

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties(mastername=mastername,
                     buildername=buildername,
                     slavename='slavename',
                     BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']) +
      api.platform(bot_config['testing']['platform'],
                   chromium_kwargs.get('TARGET_BITS', 64))
    )

    if revision:
      test += api.properties(revision=revision)

    if mastername.startswith('tryserver'):
      test += api.properties(patch_url='try_job_svn_patch')
    return test

  for mastername, master_config in BUILDERS.iteritems():
    for buildername in master_config['builders'].keys():
      yield generate_builder(mastername, buildername, revision='12345')

  # Forced builds (not specifying any revision) and test failures.
  mastername = 'client.libyuv'
  yield generate_builder(mastername, 'Linux64 Debug', revision=None,
                         suffix='_forced')
  yield generate_builder(mastername, 'Android Debug', revision=None,
                         suffix='_forced')

  yield generate_builder('tryserver.libyuv', 'linux', revision=None,
                         suffix='_forced')
