# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'isolate',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step_history',
]


class ArchiveBuildStep(object):
  def __init__(self, gs_bucket, gs_acl=None):
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl

  def run(self, api):
    return api.chromium.archive_build(
        'archive build',
        self.gs_bucket,
        gs_acl=self.gs_acl,
    )

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
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return api.chromium_android.run_test_suite(self.name, self.args)

    return api.chromium.runtest(self.name,
                                test_type=self.name,
                                args=self.args,
                                annotate='gtest',
                                xvfb=True,
                                parallel=True,
                                flakiness_dash=self.flakiness_dash)

  def compile_targets(self, api):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return [self.name + '_apk']

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

  def _get_test_spec(self, api):
    all_test_specs = api.step_history['read test spec'].json.output
    return all_test_specs.get(self.buildername, {})

  def _get_tests(self, api):
    return [self._canonicalize_test(t) for t in
            self._get_test_spec(api).get('gtest_tests', [])]

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
    explicit_targets = self._get_test_spec(api).get('compile_targets', [])
    test_targets = [t['test'] for t in self._get_tests(api)]
    # Remove duplicates.
    return sorted(set(explicit_targets + test_targets))


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


class AndroidInstrumentationTest(object):
  def __init__(self, name, compile_target, test_data=None,
               adb_install_apk=None):
    self.name = name
    self.compile_target = compile_target

    self.test_data = test_data
    self.adb_install_apk = adb_install_apk

  def run(self, api):
    assert api.chromium.c.TARGET_PLATFORM == 'android'
    if self.adb_install_apk:
      yield api.chromium_android.adb_install_apk(
          self.adb_install_apk[0], self.adb_install_apk[1])
    yield api.chromium_android.run_instrumentation_suite(
        self.name, test_data=self.test_data,
        flakiness_dashboard='test-results.appspot.com',
        verbose=True)

  def compile_targets(self, _):
    return [self.compile_target]


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
          ArchiveBuildStep(
              'chromium-browser-snapshots',
              gs_acl='public-read',
          ),
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
    'settings': {
      'build_gs_bucket': 'chromium-fyi-archive',
    },
    'builders': {
      'Linux ARM Cross-Compile': {
        # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
        'recipe_config': 'chromium_no_goma',
        'GYP_DEFINES': {
          'target_arch': 'arm',
          'arm_float_abi': 'hard',
          'test_isolation_mode': 'archive',
        },
        'chromium_config': 'chromium',
        'runhooks_env': {
          'AR': 'arm-linux-gnueabihf-ar',
          'AS': 'arm-linux-gnueabihf-as',
          'CC': 'arm-linux-gnueabihf-gcc',
          'CC_host': 'gcc',
          'CXX': 'arm-linux-gnueabihf-g++',
          'CXX_host': 'g++',
          'RANLIB': 'arm-linux-gnueabihf-ranlib',
        },
        'tests': [
          DynamicGTestTests('Linux ARM Cross-Compile'),
        ],
        'testing': {
          'platform': 'linux',
        },
        'do_not_run_tests': True,
        'use_isolate': True,
      },
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
      'Chromium Linux MSan Builder': {
        'recipe_config': 'chromium_clang',
        'GYP_DEFINES': {
          'msan': 1,
          'use_instrumented_libraries': 1,
          'instrumented_libraries_jobs': 5,
        },
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Chromium Linux MSan': {
        'recipe_config': 'chromium_clang',
        'GYP_DEFINES': {
          # Required on testers to pass the right runtime flags.
          # TODO(earthdok): make this part of a chromium_msan recipe config.
          'msan': 1,
        },
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Chromium Linux MSan'),
        ],
        'parent_buildername': 'Chromium Linux MSan Builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Chromium Linux MSan (browser tests)': {
        'recipe_config': 'chromium_clang',
        'GYP_DEFINES': {
          # Required on testers to pass the right runtime flags.
          # TODO(earthdok): make this part of a chromium_msan recipe config.
          'msan': 1,
        },
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'tests': [
          DynamicGTestTests('Chromium Linux MSan (browser tests)'),
        ],
        'parent_buildername': 'Chromium Linux MSan Builder',
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

      'Android Builder (dbg)': {
        'recipe_config': 'chromium_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'android_config': 'main_builder',
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Tests (dbg)': {
        'recipe_config': 'chromium_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Builder (dbg)',
        'android_config': 'tests_base',
        'tests': [
          GTestTest('base_unittests'),
          AndroidInstrumentationTest('MojoTest', 'mojo_test_apk'),
          AndroidInstrumentationTest(
              'AndroidWebViewTest', 'android_webview_test_apk',
              test_data='webview:android_webview/test/data/device_files',
              adb_install_apk=(
                  'AndroidWebView.apk', 'org.chromium.android_webview.shell')),
          AndroidInstrumentationTest(
              'ChromeShellTest', 'chrome_shell_test_apk',
              test_data='chrome:chrome/test/data/android/device_files',
              adb_install_apk=(
                  'ChromeShell.apk', 'org.chromium.chrome.shell')),
          AndroidInstrumentationTest(
              'ContentShellTest', 'content_shell_test_apk',
              test_data='content:content/test/data/android/device_files',
              adb_install_apk=(
                  'ContentShell.apk', 'org.chromium.content_shell_apk')),
        ],
        'testing': {
          'platform': 'linux',
        },
      },

      'Android Builder': {
        'recipe_config': 'chromium_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'android_config': 'main_builder',
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Tests': {
        'recipe_config': 'chromium_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Builder',
        'android_config': 'tests_base',
        'tests': [
          GTestTest('base_unittests'),
          AndroidInstrumentationTest('MojoTest', 'mojo_test_apk'),
          AndroidInstrumentationTest(
              'AndroidWebViewTest', 'android_webview_test_apk',
              test_data='webview:android_webview/test/data/device_files',
              adb_install_apk=(
                  'AndroidWebView.apk', 'org.chromium.android_webview.shell')),
          AndroidInstrumentationTest(
              'ChromeShellTest', 'chrome_shell_test_apk',
              test_data='chrome:chrome/test/data/android/device_files',
              adb_install_apk=(
                  'ChromeShell.apk', 'org.chromium.chrome.shell')),
          AndroidInstrumentationTest(
              'ContentShellTest', 'content_shell_test_apk',
              test_data='content:content/test/data/android/device_files',
              adb_install_apk=(
                  'ContentShell.apk', 'org.chromium.content_shell_apk')),
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
        'chromium_apply_config': ['shared_library'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'all',
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
        'chromium_apply_config': ['shared_library'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'compile_targets': [
          'all',
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
  'chromium_android': {
    'chromium_config': 'android',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
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
  # Set GYP_DEFINES explicitly because chromium config constructor does
  # not support that.
  api.chromium.c.gyp_env.GYP_DEFINES.update(bot_config.get('GYP_DEFINES', {}))
  if bot_config.get('use_isolate'):
    api.isolate.set_isolate_environment(api.chromium.c)
  for c in recipe_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  api.gclient.set_config(recipe_config['gclient_config'])
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if 'android_config' in bot_config:
    api.chromium_android.set_config(
        bot_config['android_config'],
        **bot_config.get('chromium_config_kwargs', {}))

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
    yield api.chromium.runhooks(env=bot_config.get('runhooks_env', {}))

  test_spec_file = bot_config.get('testing', {}).get('test_spec_file',
                                                     '%s.json' % mastername)
  test_spec_path = api.path['checkout'].join('testing', 'buildbot',
                                             test_spec_file)
  def test_spec_followup_fn(step_result):
    step_result.presentation.step_text = 'path: %s' % test_spec_path
  yield api.json.read(
      'read test spec',
      test_spec_path,
      step_test_data=lambda: api.json.test_api.output({}),
      followup_fn=test_spec_followup_fn),
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

    if api.chromium.c.TARGET_PLATFORM == 'android':
      steps.extend([
          api.chromium_android.checklicenses(),
          api.chromium_android.findbugs(),
      ])

  if bot_config.get('use_isolate'):
    test_args_map = {}
    test_spec = api.step_history['read test spec'].json.output
    gtests_tests = test_spec.get(buildername, {}).get('gtest_tests', [])
    for test in gtests_tests:
      if isinstance(test, dict):
        test_args = test.get('args')
        test_name = test.get('test')
        if test_name and test_args:
          test_args_map[test_name] = test_args
    steps.append(api.isolate.find_isolated_tests(api.chromium.output_dir))

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

  if (api.chromium.c.TARGET_PLATFORM == 'android' and
      bot_type in ['tester', 'builder_tester']):
    steps.append(api.chromium_android.common_tests_setup_steps())

  if not bot_config.get('do_not_run_tests'):
    test_steps = [t.run(api) for t in bot_config.get('tests', [])]
    steps.extend(api.chromium.setup_tests(bot_type, test_steps))

  if (api.chromium.c.TARGET_PLATFORM == 'android' and
      bot_type in ['tester', 'builder_tester']):
    steps.append(api.chromium_android.common_tests_final_steps())

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
      if bot_config.get('parent_buildername'):
        test += api.properties(parent_got_revision='1111111')

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

  yield (
    api.test('dynamic_gtest_win') +
    api.properties.generic(mastername='chromium.win',
                           buildername='Win7 Tests (1)',
                           parent_buildername='Win Builder') +
    api.platform('win', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Win7 Tests (1)': {
        'gtest_tests': [
          'aura_unittests',
          {'test': 'browser_tests', 'shard_index': 0, 'total_shards': 2},
        ],
      },
    }))
  )


  yield (
    api.test('arm') +
    api.properties.generic(mastername='chromium.fyi',
                           buildername='Linux ARM Cross-Compile') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Linux ARM Cross-Compile': {
        'compile_targets': ['browser_tests_run'],
        'gtest_tests': [{
          'test': 'browser_tests',
          'args': ['--gtest-filter', '*NaCl*'],
          'shard_index': 0,
          'total_shards': 1,
        }],
      },
    }))
  )

  yield (
    api.test('findbugs_failure') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Android Builder (dbg)') +
    api.platform('linux', 32) +
    api.step_data('findbugs', retcode=1)
  )

  yield (
    api.test('msan') +
    api.properties.generic(mastername='chromium.fyi',
                           buildername='Chromium Linux MSan',
                           parent_buildername='Chromium Linux MSan Builder') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Chromium Linux MSan': {
        'compile_targets': ['base_unittests'],
        'gtest_tests': ['base_unittests'],
      },
    }))
  )
