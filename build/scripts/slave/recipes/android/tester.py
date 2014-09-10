# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'bot_update',
    'chromium_android',
    'gclient',
    'json',
    'path',
    'properties',
    'tryserver',
]

BUILDERS = {
  'tryserver.chromium.linux': {
    'android_dbg_tests_recipe': {
      'config': 'main_builder',
      'instrumentation_tests': [
        {
          'test': 'MojoTest',
        },
        {
          'install': {
            'package': 'org.chromium.android_webview.shell',
            'apk': 'AndroidWebView.apk'
          },
          'test': 'AndroidWebViewTest',
          'kwargs': {
            'test_data': 'webview:android_webview/test/data/device_files',
          },
        },
        {
          'install': {
            'package': 'org.chromium.chrome.shell',
            'apk': 'ChromeShell.apk',
          },
          'test': 'ChromeShellTest',
          'kwargs': {
            'test_data': 'chrome:chrome/test/data/android/device_files',
            # TODO(luqui): find out if host_driven_root is necessary
          },
        },
        {
          'install': {
            'package': 'org.chromium.chontent_shell_apk',
            'apk': 'ContentShell.apk',
          },
          'test': 'ContentShellTest',
          'kwargs': {
            'test_data': 'content:content/test/data/android/device_files',
          },
        },
      ],
      'unittests': [
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
      ],
      'target': 'Debug',
      'try': True,
    },
  }
}

def GenSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config = BUILDERS[mastername][buildername]

  api.chromium_android.configure_from_properties(
      bot_config['config'],
      INTERNAL=False,
      BUILD_CONFIG='Debug',
      REPO_NAME='src',
      REPO_URL='svn://svn-mirror.golo.chromium.org/chrome/trunk/src')

  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.gclient.apply_config('chrome_internal')

  api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()
  api.chromium_android.runhooks()

  if bot_config.get('try', False):
    api.tryserver.maybe_apply_issue()

  api.chromium_android.run_tree_truth()
  api.chromium_android.compile()

  api.adb.root_devices()

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.detect_and_setup_devices()

  instrumentation_tests = bot_config.get('instrumentation_tests', [])
  for suite in instrumentation_tests:
    if 'install' in suite:
      api.chromium_android.adb_install_apk(
          suite['install']['apk'],
          suite['install']['package'])
    #TODO(martiniss) convert loop
    api.chromium_android.run_instrumentation_suite(
        suite['test'], verbose=True, **suite.get('kwargs', {}))

  unittests = bot_config.get('unittests', [])
  for suite, isolate_path in unittests:
    if isolate_path:
      isolate_path = api.path['checkout'].join(*isolate_path)
    #TODO(martiniss) convert loop
    api.chromium_android.run_test_suite(
        suite,
        isolate_file_path=isolate_path)

  api.chromium_android.logcat_dump(gs_bucket='chromium-android')
  api.chromium_android.stack_tool_steps()
  api.chromium_android.test_report()

def GenTests(api):
  for mastername in BUILDERS:
    for buildername in BUILDERS[mastername]:
      yield (
          api.test(buildername) +
          api.properties.generic(
              revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
              parent_buildername='parent_buildername',
              parent_buildnumber='1729',
              mastername=mastername,
              buildername=buildername,
              slavename='slavename',
              buildnumber='1337')
      )
