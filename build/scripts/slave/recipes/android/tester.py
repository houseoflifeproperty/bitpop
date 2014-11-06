# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'bot_update',
    'chromium',
    'chromium_android',
    'filter',
    'gclient',
    'json',
    'path',
    'properties',
    'step',
    'tryserver',
]

INSTRUMENTATION_TESTS = [
  {
    'test': 'MojoTest',
    'gyp_target': 'mojo_test_apk',
  },
  {
    'test': 'AndroidWebViewTest',
    'gyp_target': 'android_webview_test_apk',
    'kwargs': {
      'test_data': 'webview:android_webview/test/data/device_files',
      'install_apk': {
        'package': 'org.chromium.android_webview.shell',
        'apk': 'AndroidWebView.apk'
      },
    },
  },
  {
    'test': 'ChromeShellTest',
    'gyp_target': 'chrome_shell_test_apk',
    'kwargs': {
      'test_data': 'chrome:chrome/test/data/android/device_files',
      'install_apk': {
        'package': 'org.chromium.chrome.shell',
        'apk': 'ChromeShell.apk',
      },
      # TODO(luqui): find out if host_driven_root is necessary
    },
  },
  {
    'test': 'ContentShellTest',
    'gyp_target': 'content_shell_test_apk',
    'kwargs': {
      'test_data': 'content:content/test/data/android/device_files',
      'install_apk': {
        'package': 'org.chromium.chontent_shell_apk',
        'apk': 'ContentShell.apk',
      },
    },
  },
]

UNIT_TESTS = [
  [ 'base_unittests', None ],
  [ 'breakpad_unittests', [ 'breakpad', 'breakpad_unittests.isolate' ] ],
  [ 'cc_unittests', None ],
  [ 'components_unittests', None ],
  [ 'content_browsertests',  None ],
  [ 'content_unittests', None ],
  [ 'events_unittests', None ],
  [ 'gl_tests', None ],
  [ 'gpu_unittests', None ],
  [ 'ipc_tests', None ],
  [ 'media_unittests', None ],
  [ 'net_unittests', None ],
  [ 'sandbox_linux_unittests', None ],
  [ 'sql_unittests', None ],
  [ 'sync_unit_tests', None ],
  [ 'ui_unittests', None ],
  [ 'unit_tests', None ],
  [ 'webkit_unit_tests', None ],
]

JAVA_UNIT_TESTS = [
  'junit_unit_tests',
]

BUILDERS = {
  'tryserver.chromium.linux': {
    'android_dbg_tests_recipe': {
      'config': 'main_builder',
      'instrumentation_tests': INSTRUMENTATION_TESTS,
      'unittests': UNIT_TESTS,
      'java_unittests': JAVA_UNIT_TESTS,
      'target': 'Debug',
      'try': True,
    },
    'android_rel_tests_recipe': {
      'config': 'main_builder',
      'instrumentation_tests': INSTRUMENTATION_TESTS,
      'unittests': [],
      'telemetry_unittests': True,
      'telemetry_perf_unittests': True,
      'java_unittests': JAVA_UNIT_TESTS,
      'target': 'Release',
      'try': True,
    },
  },
  'chromium.fyi': {
    'Android Tests (dbg)': {
      'config': 'main_builder',
      'instrumentation_tests': INSTRUMENTATION_TESTS,
      'unittests': UNIT_TESTS,
      'java_unittests': [],
      'target': 'Debug',
      'download': {
        'bucket': 'chromium-android',
        'path': lambda api: ('android_fyi_dbg/full-build-linux_%s.zip' %
                             api.properties['revision']),
      },
    },
    'Android Tests': {
      'config': 'main_builder',
      'instrumentation_tests': INSTRUMENTATION_TESTS,
      'unittests': UNIT_TESTS,
      'java_unittests': [],
      'target': 'Release',
      'download': {
        'bucket': 'chromium-android',
        'path': lambda api: ('android_fyi_rel/full-build-linux_%s.zip' %
                             api.properties['revision']),
      },
    },
  }

}

def GenSteps(api):
  # Required for us to be able to use filter.
  api.chromium_android.set_config('base_config')

  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config = BUILDERS[mastername][buildername]

  api.chromium_android.configure_from_properties(
      bot_config['config'],
      INTERNAL=False,
      BUILD_CONFIG=bot_config['target'],
      REPO_NAME='src',
      REPO_URL='svn://svn-mirror.golo.chromium.org/chrome/trunk/src')

  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.gclient.apply_config('chrome_internal')

  api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()
  api.chromium_android.runhooks()

  compile_targets = None
  instrumentation_tests = bot_config.get('instrumentation_tests', [])
  unittests = bot_config.get('unittests', [])
  java_unittests = bot_config.get('java_unittests', [])
  is_trybot = bot_config.get('try', False)
  if is_trybot:
    api.tryserver.maybe_apply_issue()

    # Early out if we haven't changed any relevant code.
    test_names = []
    test_names.extend([suite['gyp_target'] for suite in instrumentation_tests])
    test_names.extend([suite for suite, _ in unittests])
    test_names.extend(java_unittests)

    compile_targets = api.chromium.c.compile_py.default_targets
    api.filter.does_patch_require_compile(
        exes=test_names,
        compile_targets=compile_targets,
        additional_name='chromium',
        config_file_name='trybot_analyze_config.json')
    if not api.filter.result:
      return
    compile_targets = list(set(compile_targets) &
                                 set(api.filter.compile_targets)) if \
        compile_targets else api.filter.compile_targets
    instrumentation_tests = [i for i in instrumentation_tests if \
        i['gyp_target'] in api.filter.matching_exes]
    unittests = [i for i in unittests if i[0] in api.filter.matching_exes]
    java_unittests = [i for i in java_unittests
                      if i in api.filter.matching_exes]

  api.chromium_android.run_tree_truth()

  if bot_config.get('download'):
    api.chromium_android.download_build(bot_config['download']['bucket'],
                                        bot_config['download']['path'](api))
  else:
    api.chromium_android.compile(targets=compile_targets)

  if not instrumentation_tests and not unittests and not java_unittests:
    return

  api.adb.root_devices()

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.detect_and_setup_devices()

  with api.step.defer_results():
    for suite in instrumentation_tests:
      api.chromium_android.run_instrumentation_suite(
          suite['test'], verbose=True, **suite.get('kwargs', {}))

    for suite, isolate_path in unittests:
      if isolate_path:
        isolate_path = api.path['checkout'].join(*isolate_path)
      api.chromium_android.run_test_suite(
          suite,
          isolate_file_path=isolate_path)

    if bot_config.get('telemetry_unittests'):
      api.chromium.run_telemetry_unittests()
    if bot_config.get('telemetry_perf_unittests'):
      api.chromium.run_telemetry_perf_unittests()

    for suite in java_unittests:
      api.chromium_android.run_java_unit_test_suite(suite)

    api.chromium_android.logcat_dump(gs_bucket='chromium-android')
    api.chromium_android.stack_tool_steps()
    api.chromium_android.test_report()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername in BUILDERS:
    for buildername in BUILDERS[mastername]:
      bot_config = BUILDERS[mastername][buildername]
      test_props = (api.test(_sanitize_nonalpha('%s_%s' %
                                                (mastername, buildername))) +
                    api.properties.generic(
                        revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
                        parent_buildername='parent_buildername',
                        parent_buildnumber='1729',
                        mastername=mastername,
                        buildername=buildername,
                        slavename='slavename',
                        buildnumber='1337'))

      if bot_config.get('try'):
        test_props += api.override_step_data(
            'analyze',
            api.json.output({'status': 'Found dependency',
                             'targets': ['breakpad_unittests',
                                         'chrome_shell_test_apk',
                                         'junit_unit_tests'],
                             'build_targets': ['breakpad_unittests',
                                               'chrome_shell_test_apk',
                                               'junit_unit_tests']}))
      yield test_props

  yield (
      api.test('android_dbg_tests_recipe__content_browsertests_failure') +
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='android_dbg_tests_recipe',
          slavename='slavename') +
      api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                           'targets': ['content_browsertests'],
                           'build_targets': ['content_browsertests']})) +
      api.step_data('content_browsertests', retcode=1)
  )

  yield (
      api.test('no_provision_devices_when_no_tests') +
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='android_dbg_tests_recipe',
          slavename='slavename') +
      api.override_step_data(
          'analyze',
          api.json.output({'status': 'Found dependency',
                           'targets': [],
                           'build_targets': ['content_browsertests']}))
  )

  # Tests analyze module early exits if patch can't affect this config.
  yield (
      api.test('no_compile_because_of_analyze') +
      api.properties.generic(
          mastername='tryserver.chromium.linux',
          buildername='android_dbg_tests_recipe',
          slavename='slavename') +
      api.override_step_data(
          'analyze',
          api.json.output({'status': 'No compile necessary'}))
  )
