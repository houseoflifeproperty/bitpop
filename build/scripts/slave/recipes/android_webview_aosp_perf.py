# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Performance testing for the WebView.
"""

DEPS = [
  'android',
  'json',
  'properties',
  'path',
  'step',
  'gclient',
  'python',
  'chromium_android',
  'adb',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

PERF_TESTS = {
  "steps": {
    "sunspider": {
      "cmd": "tools/perf/run_benchmark" \
             " -v" \
             " --browser=android-webview" \
             " --extra-browser-args=--spdy-proxy-origin" \
             " --show-stdout sunspider",
      "device_affinity": 0,
    },
    "page_cycler.bloat": {
      "cmd": "tools/perf/run_benchmark" \
             " -v" \
             " --browser=android-webview" \
             " --extra-browser-args=--spdy-proxy-origin" \
             " --show-stdout page_cycler.bloat",
      "device_affinity": 1,
    },
  },
  "version": 1,
}

TELEMETRY_SHELL_APK = 'AndroidWebViewTelemetryShell.apk'
TELEMETRY_SHELL_PACKAGE = 'org.chromium.telemetry_shell'

BUILDER = {
  'perf_id': 'android-webview',
  'num_device_shards': 2,
}

def GenSteps(api):
  api.chromium_android.configure_from_properties('base_config',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')

  droid = api.android
  droid.set_config('AOSP_webview')

  # add chrome src-internal deps needed for page_cycler page sets.
  spec = droid.create_spec()
  api.gclient.apply_config('chrome_internal', spec)

  # re-include page_cycler dep, which is excluded by default in chrome_internal.
  del spec.solutions[1].custom_deps['src/data/page_cycler']

  # Sync code.
  droid.sync_chromium(spec)

  # Use our adb
  api.adb.adb_path = str(
    api.path['checkout'].join('third_party', 'android_tools',
                              'sdk', 'platform-tools', 'adb'))

  # Gyp the chromium checkout.
  api.step(
      'gyp_chromium',
      [api.path['checkout'].join('build', 'gyp_chromium'), '-DOS=android'],
      cwd=api.path['checkout'])

  # Build the webview shell and chromium parts.
  droid.compile_step(
    step_name='compile android_webview',
    build_tool='ninja',
    targets=['android_webview_apk', 'android_webview_telemetry_shell_apk'],
    use_goma=True,
    src_dir=api.path['checkout'])

  # Build tools.
  droid.compile_step(
    step_name='compile android_tools',
    build_tool='ninja',
    targets=['android_tools'],
    use_goma=True,
    src_dir=api.path['checkout'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  # TODO(hjd): Do special WebView provision.
  api.chromium_android.provision_devices()

  # TODO(hjd): Push the WebView files to the devices.

  # Install the telemetry shell.
  api.chromium_android.adb_install_apk(TELEMETRY_SHELL_APK,
                                       TELEMETRY_SHELL_PACKAGE)

  # TODO(hjd): Start using list_perf_tests
  try:
    api.chromium_android.run_sharded_perf_tests(
      config=api.json.input(data=PERF_TESTS),
      perf_id=BUILDER['perf_id'])
  finally:
    api.chromium_android.logcat_dump()
    api.chromium_android.stack_tool_steps()
    api.chromium_android.test_report()


def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()

