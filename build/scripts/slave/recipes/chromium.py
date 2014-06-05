# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step_history',
]


class ArchiveBuildStep(object):
  def __init__(self, gs_bucket):
    self.gs_bucket = gs_bucket

  def run(self, api):
    return api.chromium.archive_build(
        'archive build', self.gs_bucket)

  @staticmethod
  def compile_targets(_):
    return []


class CheckpermsTest(object):
  @staticmethod
  def run(api):
    return api.chromium.checkperms()

  @staticmethod
  def compile_targets(_):
    return []


class Deps2GitTest(object):
  @staticmethod
  def run(api):
    return api.chromium.deps2git()

  @staticmethod
  def compile_targets(_):
    return []


class Deps2SubmodulesTest(object):
  @staticmethod
  def run(api):
    return api.chromium.deps2submodules()

  @staticmethod
  def compile_targets(_):
    return []


class GTestTest(object):
  def __init__(self, name, args=None, flakiness_dash=False):
    self.name = name
    self.args = args or []
    self.flakiness_dash = flakiness_dash

  def run(self, api):
    return api.chromium.runtest(self.name,
                                test_type=self.name,
                                args=self.args,
                                annotate='gtest',
                                xvfb=True,
                                parallel=True,
                                flakiness_dash=self.flakiness_dash)

  def compile_targets(self, _):
    return [self.name]


class DynamicGTestTests(object):
  def __init__(self, buildername, flakiness_dash=True):
    self.buildername = buildername
    self.flakiness_dash = flakiness_dash

  @staticmethod
  def _canonicalize_test(test):
    if isinstance(test, basestring):
      return {'test': test, 'shard_index': 0, 'total_shards': 1}
    return test

  def _get_tests(self, api):
    test_spec = api.step_history['read test spec'].json.output
    return [self._canonicalize_test(t) for t in
            test_spec.get(self.buildername, {}).get('gtest_tests', [])]

  def run(self, api):
    steps = []
    for test in self._get_tests(api):
      args = []
      if test['shard_index'] != 0 or test['total_shards'] != 1:
        args.extend(['--test-launcher-shard-index=%d' % test['shard_index'],
                     '--test-launcher-total-shards=%d' % test['total_shards']])
      steps.append(api.chromium.runtest(
          test['test'], test_type=test['test'], args=args, annotate='gtest',
          xvfb=True, parallel=True, flakiness_dash=self.flakiness_dash))

    return steps

  def compile_targets(self, api):
    return [t['test'] for t in self._get_tests(api)]


class TelemetryUnitTests(object):
  @staticmethod
  def run(api):
    return api.chromium.run_telemetry_unittests()

  @staticmethod
  def compile_targets(_):
    return ['chrome']

class TelemetryPerfUnitTests(object):
  @staticmethod
  def run(api):
    return api.chromium.run_telemetry_perf_unittests()

  @staticmethod
  def compile_targets(_):
    return ['chrome']


class NaclIntegrationTest(object):
  @staticmethod
  def run(api):
    args = [
      '--mode', api.chromium.c.BUILD_CONFIG,
    ]
    return api.python(
        'nacl_integration',
        api.path['checkout'].join('chrome',
                                  'test',
                                  'nacl_test_injection',
                                  'buildbot_nacl_integration.py'),
        args)

  @staticmethod
  def compile_targets(_):
    return ['chrome']


# Make it easy to change how different configurations of this recipe
# work without making buildbot-side changes. This contains a dictionary
# of buildbot masters, and each of these dictionaries maps a builder name
# to one of recipe configs below.
BUILDERS = {
  'chromium.chrome': {
    'builders': {
      'Google Chrome ChromeOS': {
        'recipe_config': 'chromeos_official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_targets': [
          'chrome',
          'chrome_sandbox',
          'linux_symbols',
          'symupload'
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Google Chrome Linux': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'Google Chrome Linux x64': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {
          'platform': 'linux',
        },
      },
      'Google Chrome Mac': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {
          'platform': 'mac',
        },
      },
      'Google Chrome Win': {
        'recipe_config': 'official',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
  'chromium.chromiumos': {
    'settings': {
      'build_gs_bucket': 'chromium-chromiumos-archive',
    },
    'builders': {
      'Linux ChromiumOS Full': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'compile_targets': [
          'app_list_unittests',
          'aura_builder',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'chromeos_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'gcm_unit_tests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'message_center_unittests',
          'nacl_loader_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
        ],
        'tests': [
          ArchiveBuildStep('chromium-browser-snapshots'),
          Deps2GitTest(),
          Deps2SubmodulesTest(),
          CheckpermsTest(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux ChromiumOS Builder': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'aura_builder',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (1)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux ChromiumOS Tests (1)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'parent_buildername': 'Linux ChromiumOS Builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (2)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux ChromiumOS Tests (2)'),
        ],
        'parent_buildername': 'Linux ChromiumOS Builder',
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux ChromiumOS (Clang dbg)': {
        'recipe_config': 'chromium_chromeos_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_targets': [
          'app_list_unittests',
          'aura_builder',
          'base_unittests',
          'browser_tests',
          'cacheinvalidation_unittests',
          'chromeos_unittests',
          'components_unittests',
          'compositor_unittests',
          'content_browsertests',
          'content_unittests',
          'crypto_unittests',
          'dbus_unittests',
          'device_unittests',
          'gcm_unit_tests',
          'google_apis_unittests',
          'gpu_unittests',
          'interactive_ui_tests',
          'ipc_tests',
          'jingle_unittests',
          'media_unittests',
          'message_center_unittests',
          'nacl_loader_unittests',
          'net_unittests',
          'ppapi_unittests',
          'printing_unittests',
          'remoting_unittests',
          'sandbox_linux_unittests',
          'sql_unittests',
          'sync_unit_tests',
          'ui_unittests',
          'unit_tests',
          'url_unittests',
          'views_unittests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux ChromiumOS Builder (dbg)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'aura_builder',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (dbg)(1)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux ChromiumOS Tests (dbg)(1)'),
        ],
        'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (dbg)(2)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux ChromiumOS Tests (dbg)(2)'),
        ],
        'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux ChromiumOS Tests (dbg)(3)': {
        'recipe_config': 'chromium_chromeos',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux ChromiumOS Tests (dbg)(3)'),
        ],
        'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'chromium.git': {
    'builders': {
      'WinGit': {
          'recipe_config': 'chromium',
          'testing': {'platform': 'win'},
      },
      'WinGitXP': {
          'recipe_config': 'chromium',
          'testing': {'platform': 'win'},
      },
      'MacGit': {
          'recipe_config': 'chromium',
          'testing': {'platform': 'mac'},
      },
      'LinuxGit': {
          'recipe_config': 'chromium',
          'testing': {'platform': 'linux'},
      },
      'LinuxGit x64': {
          'recipe_config': 'chromium',
          'testing': {'platform': 'linux'},
      },
    }
  },
  'chromium.fyi': {
    'builders': {
      'Linux Trusty': {
        # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
        'recipe_config': 'chromium_no_goma',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'compile_targets': [
          'all',
        ],
        'tests': [
          DynamicGTestTests('Linux Trusty'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Trusty (32)': {
        # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
        'recipe_config': 'chromium_no_goma',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'compile_targets': [
          'all',
        ],
        'tests': [
          DynamicGTestTests('Linux Trusty (32)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Trusty (dbg)': {
        # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
        'recipe_config': 'chromium_no_goma',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'compile_targets': [
          'all',
        ],
        'tests': [
          DynamicGTestTests('Linux Trusty (dbg)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Trusty (dbg)(32)': {
        # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
        'recipe_config': 'chromium_no_goma',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'compile_targets': [
          'all',
        ],
        'tests': [
          DynamicGTestTests('Linux Trusty (dbg)(32)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'chromium.linux': {
    'settings': {
      'build_gs_bucket': 'chromium-linux-archive',
    },
    'builders': {
      'Linux Builder': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_swarm_tests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux Tests'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'parent_buildername': 'Linux Builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Sync': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          GTestTest('sync_integration_tests', args=[
              '--ui-test-action-max-timeout=120000'
          ]),
        ],
        'parent_buildername': 'Linux Builder',
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux Builder (dbg)(32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'google_apis_unittests',
          'sync_integration_tests',
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests (dbg)(1)(32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux Tests (dbg)(1)(32)'),
        ],
        'parent_buildername': 'Linux Builder (dbg)(32)',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests (dbg)(2)(32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux Tests (dbg)(2)(32)'),
          NaclIntegrationTest(),
        ],
        'parent_buildername': 'Linux Builder (dbg)(32)',
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux Builder (dbg)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests (dbg)(1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux Tests (dbg)(1)'),
        ],
        'parent_buildername': 'Linux Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tests (dbg)(2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Linux Tests (dbg)(2)'),
          NaclIntegrationTest(),
        ],
        'parent_buildername': 'Linux Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },

      'Linux Clang (dbg)': {
        'recipe_config': 'chromium_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_targets': [
          'all',
        ],
        'tests': [
          DynamicGTestTests('Linux Clang (dbg)'),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'chromium.mac': {
    'settings': {
      'build_gs_bucket': 'chromium-mac-archive',
    },
    'builders': {
      'Mac Builder': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_builder_tests',
        ],
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.6 Tests (1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac10.6 Tests (1)'),
          NaclIntegrationTest(),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.6 Tests (2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac10.6 Tests (2)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.6 Tests (3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac10.6 Tests (3)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.7 Tests (1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac10.7 Tests (1)'),
          NaclIntegrationTest(),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.7 Tests (2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac10.7 Tests (2)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.7 Tests (3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac10.7 Tests (3)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac10.6 Sync': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'tests': [
          GTestTest('sync_integration_tests', args=[
              '--ui-test-action-max-timeout=120000'
          ]),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac Builder (dbg)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_builder_tests',
        ],
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.6 Tests (dbg)(1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.6 Tests (dbg)(1)'),
          NaclIntegrationTest(),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.6 Tests (dbg)(2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.6 Tests (dbg)(2)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.6 Tests (dbg)(3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.6 Tests (dbg)(3)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.6 Tests (dbg)(4)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.6 Tests (dbg)(4)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.7 Tests (dbg)(1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.7 Tests (dbg)(1)'),
          NaclIntegrationTest(),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.7 Tests (dbg)(2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.7 Tests (dbg)(2)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.7 Tests (dbg)(3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.7 Tests (dbg)(3)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac 10.7 Tests (dbg)(4)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'tests': [
          DynamicGTestTests('Mac 10.7 Tests (dbg)(4)'),
        ],
        'bot_type': 'tester',
        'parent_buildername': 'Mac Builder (dbg)',
        'testing': {
          'platform': 'mac',
        }
      },
    },
  },
  'chromium.win': {
    'settings': {
      'build_gs_bucket': 'chromium-win-archive',
    },
    'builders': {
      'Win Builder': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_builder_tests',
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'XP Tests (1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('XP Tests (1)'),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'XP Tests (2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('XP Tests (2)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'XP Tests (3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('XP Tests (3)'),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Vista Tests (1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Vista Tests (1)'),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Vista Tests (2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Vista Tests (2)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Vista Tests (3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Vista Tests (3)'),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (1)'),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (2)'),
          TelemetryUnitTests(),
          TelemetryPerfUnitTests(),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (3)'),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Sync': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          GTestTest('sync_integration_tests', args=[
              '--ui-test-action-max-timeout=120000'
          ]),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },

      'Win x64 Builder': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_builder_tests',
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win 7 Tests x64 (1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win 7 Tests x64 (1)'),
        ],
        'parent_buildername': 'Win x64 Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win 7 Tests x64 (2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win 7 Tests x64 (2)'),
        ],
        'parent_buildername': 'Win x64 Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win 7 Tests x64 (3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win 7 Tests x64 (3)'),
          TelemetryUnitTests(),
        ],
        'parent_buildername': 'Win x64 Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Sync x64': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          GTestTest('sync_integration_tests', args=[
              '--ui-test-action-max-timeout=120000'
          ]),
        ],
        'parent_buildername': 'Win x64 Builder',
        'testing': {
          'platform': 'win',
        },
      },

      'NaCl Tests (x86-32)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          NaclIntegrationTest(),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'NaCl Tests (x86-64)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          NaclIntegrationTest(),
        ],
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },

      'Win x64 Builder (dbg)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_builder_tests',
        ],
        'testing': {
          'platform': 'win',
        },
      },

      'Win Builder (dbg)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'chromium_builder_tests',
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (dbg)(1)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (dbg)(1)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (dbg)(2)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (dbg)(2)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (dbg)(3)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (dbg)(3)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (dbg)(4)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (dbg)(4)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (dbg)(5)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (dbg)(5)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tests (dbg)(6)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win7 Tests (dbg)(6)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Interactive Tests (dbg)': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Interactive Tests (dbg)'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
      'Win8 Aura': {
        'recipe_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'disable_runhooks': True,
        'tests': [
          DynamicGTestTests('Win8 Aura'),
        ],
        'parent_buildername': 'Win Builder (dbg)',
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
}


# Different types of builds this recipe can do.
RECIPE_CONFIGS = {
  'chromeos_official': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
  },
  'chromium_clang': {
    'chromium_config': 'chromium_clang',
    'gclient_config': 'chromium',
  },
  'chromium_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_chromeos_clang': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_no_goma': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
  },
  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  master_config = master_dict.get('settings', {})
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.chromium.set_config(recipe_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  for c in recipe_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  api.gclient.set_config(recipe_config['gclient_config'])
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if api.platform.is_win:
    yield api.chromium.taskkill()

  # Bot Update re-uses the gclient configs.
  yield api.bot_update.ensure_checkout(),
  if not api.step_history.last_step().json.output['did_run']:
    yield api.gclient.checkout(),
  # Whatever step is run right before this line needs to emit got_revision.
  update_step = api.step_history.last_step()
  got_revision = update_step.presentation.properties['got_revision']

  bot_type = bot_config.get('bot_type', 'builder_tester')

  if not bot_config.get('disable_runhooks'):
    yield api.chromium.runhooks()

  yield api.json.read(
      'read test spec',
      api.path['checkout'].join('testing', 'buildbot', '%s.json' % mastername),
      step_test_data=lambda: api.json.test_api.output({})),
  yield api.chromium.cleanup_temp()

  # For non-trybot recipes we should know (seed) all steps in advance,
  # once we read the test spec. Instead of yielding single steps
  # or groups of steps, yield all of them at the end.
  steps = []

  if bot_type in ['builder', 'builder_tester']:
    compile_targets = set(bot_config.get('compile_targets', []))
    for test in bot_config.get('tests', []):
      compile_targets.update(test.compile_targets(api))
    for builder_dict in master_dict.get('builders', {}).itervalues():
      if builder_dict.get('parent_buildername') == buildername:
        for test in builder_dict.get('tests', []):
          compile_targets.update(test.compile_targets(api))
    steps.extend([
        api.chromium.compile(targets=sorted(compile_targets)),
        api.chromium.checkdeps(),
    ])

  if bot_type == 'builder':
    steps.append(api.archive.zip_and_upload_build(
        'package build',
        api.chromium.c.build_config_fs,
        api.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=api.properties['mastername']),
        build_revision=got_revision))

  if bot_type == 'tester':
    # Protect against hard to debug mismatches between directory names
    # used to run tests from and extract build to. We've had several cases
    # where a stale build directory was used on a tester, and the extracted
    # build was not used at all, leading to confusion why source code changes
    # are not taking effect.
    #
    # The best way to ensure the old build directory is not used is to
    # remove it.
    steps.append(api.path.rmtree(
      'build directory',
      api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)))

    steps.append(api.archive.download_and_unzip_build(
      'extract build',
      api.chromium.c.build_config_fs,
      api.archive.legacy_download_url(
        master_config.get('build_gs_bucket'),
        extra_url_components=api.properties['mastername'],),
      build_revision=got_revision,
      # TODO(phajdan.jr): Move abort_on_failure to archive recipe module.
      abort_on_failure=True))

  if bot_type in ['tester', 'builder_tester'] and bot_config.get('tests'):
    if api.platform.is_win:
      steps.append(api.python(
        'start_crash_service',
        api.path['build'].join('scripts', 'slave', 'chromium',
                               'run_crash_handler.py'),
        ['--target', api.chromium.c.build_config_fs]))

    steps.extend([t.run(api) for t in bot_config['tests']])

    if api.platform.is_win:
      steps.append(api.python(
        'process_dumps',
        api.path['build'].join('scripts', 'slave', 'process_dumps.py'),
        ['--target', api.chromium.c.build_config_fs]))

  # For non-trybot recipes we should know (seed) all steps in advance,
  # at the beginning of each build. Instead of yielding single steps
  # or groups of steps, yield all of them at the end.
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config.get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               parent_buildername=bot_config.get(
                                   'parent_buildername')) +
        api.platform(bot_config['testing']['platform'],
                     bot_config.get(
                         'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
      )

      if bot_type in ['builder', 'builder_tester']:
        test += api.step_data('checkdeps', api.json.output([]))

      yield test

  yield (
    api.test('dynamic_gtest') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Linux Tests': {
        'gtest_tests': [
          'base_unittests',
          {'test': 'browser_tests', 'shard_index': 0, 'total_shards': 2},
        ],
      },
    }))
  )
