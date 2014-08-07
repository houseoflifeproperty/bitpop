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
  'tryserver.chromium': {
    'android_dbg_triggered_tests_recipe': {
      'config': 'android_shared',
      'download': {
        'bucket': 'chromium-android',
        'path': lambda api: ('android_try_dbg_recipe/full-build-linux_%s.zip'
                             % api.properties['parent_buildnumber']),
      },
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
        'base_unittests',
        'breakpad_unittests',
        'cc_unittests',
        'components_unittests',
        'content_browsertests',
        'content_unittests',
        'events_unittests',
        'gl_tests',
        'gpu_unittests',
        'ipc_tests',
        'media_unittests',
        'net_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'ui_unittests',
        'unit_tests',
        'webkit_compositor_bindings_unittests',
        'webkit_unit_tests',
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
  api.chromium_android.c.set_val(bot_config.get('custom', {}))
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.gclient.apply_config('chrome_internal')

  assert 'parent_buildername' in api.properties, (
      'No parent_buildername in properties.  If you forced this build, please '
      'use Rebuild instead')

  yield api.bot_update.ensure_checkout()
  yield api.chromium_android.envsetup()
  yield api.chromium_android.runhooks()

  if bot_config.get('try', False):
    yield api.tryserver.maybe_apply_issue()

  yield api.chromium_android.clean_local_files()
  yield api.chromium_android.run_tree_truth()
  yield api.chromium_android.download_build(
      bot_config['download']['bucket'],
      bot_config['download']['path'](api))

  yield api.adb.root_devices()

  yield api.chromium_android.spawn_logcat_monitor()
  yield api.chromium_android.detect_and_setup_devices()

  instrumentation_tests = bot_config.get('instrumentation_tests', [])
  for suite in instrumentation_tests:
    if 'install' in suite:
      yield api.chromium_android.adb_install_apk(
          suite['install']['apk'],
          suite['install']['package'])
    yield api.chromium_android.run_instrumentation_suite(
        suite['test'], verbose=True, **suite.get('kwargs', {}))

  unittests = bot_config.get('unittests', [])
  for suite in unittests:
    yield api.chromium_android.run_test_suite(suite)

  yield api.chromium_android.logcat_dump()
  yield api.chromium_android.stack_tool_steps()
  yield api.chromium_android.test_report()
  yield api.chromium_android.cleanup_build()

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
