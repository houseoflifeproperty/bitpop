# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave.recipe_modules.webrtc import builders


class WebRTCApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._env = {}

  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

  NORMAL_TESTS = [
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_unittest',
    'modules_tests',
    'modules_unittests',
    'rtc_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'video_engine_tests',
    'voice_engine_unittests',
  ]

  # Android APK tests. Mapping between test name and isolate file location.
  ANDROID_APK_TESTS = {
    'audio_decoder_unittests': 'webrtc/modules/audio_coding/neteq',
    'common_audio_unittests': 'webrtc/common_audio',
    'common_video_unittests': 'webrtc/common_video',
    'modules_tests': 'webrtc/modules',
    'modules_unittests': 'webrtc/modules',
    'system_wrappers_unittests': 'webrtc/system_wrappers/source',
    'test_support_unittests': 'webrtc/test',
    'tools_unittests': 'webrtc/tools',
    'video_capture_tests': 'webrtc/modules/video_capture',
    'video_engine_tests': 'webrtc',
    'video_engine_core_unittests': 'webrtc/video_engine',
    'voice_engine_unittests': 'webrtc/voice_engine',
    'webrtc_perf_tests': 'webrtc',
  }

  # Map of GS archive names to urls.
  # TODO(kjellander): Convert to use the auto-generated URLs once we've setup a
  # separate bucket per master.
  GS_ARCHIVES = {
    'android_dbg_archive': 'gs://chromium-webrtc/android_chromium_dbg',
    'android_dbg_archive_fyi': ('gs://chromium-webrtc/'
                                'android_chromium_trunk_dbg'),
    'android_apk_dbg_archive': 'gs://chromium-webrtc/android_dbg',
    'android_apk_rel_archive': 'gs://chromium-webrtc/android_rel',
    'win_rel_archive': 'gs://chromium-webrtc/Win Builder',
    'win_rel_archive_fyi': 'gs://chromium-webrtc/win_rel-fyi',
    'mac_rel_archive': 'gs://chromium-webrtc/Mac Builder',
    'linux_rel_archive': 'gs://chromium-webrtc/Linux Builder',
  }

  DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

  def runtests(self, test_suite=None, revision=None):
    """Add a suite of test steps.

    Args:
      test_suite: The name of the test suite.
      revision: Revision for the build. Mandatory for perf measuring tests.
    """
    with self.m.step.defer_results():
      if test_suite in ('webrtc', 'webrtc_parallel'):
        parallel = test_suite.endswith('_parallel')
        for test in self.NORMAL_TESTS:
          self.add_test(test, parallel=parallel)

        if self.m.platform.is_mac and self.m.chromium.c.TARGET_BITS == 64:
          test = self.m.path.join('libjingle_peerconnection_objc_test.app',
                                  'Contents', 'MacOS',
                                  'libjingle_peerconnection_objc_test')
          self.add_test(test, name='libjingle_peerconnection_objc_test',
                        parallel=parallel)
      elif test_suite == 'webrtc_baremetal':
        # Add baremetal tests, which are different depending on the platform.
        if self.m.platform.is_win or self.m.platform.is_mac:
          self.add_test('audio_device_tests')
        elif self.m.platform.is_linux:
          f = self.m.path['checkout'].join
          self.add_test(
              'audioproc',
              args=['-aecm', '-ns', '-agc', '--fixed_digital', '--perf', '-pb',
                    f('resources', 'audioproc.aecdump')],
              revision=revision,
              perf_test=True)
          self.add_test(
              'iSACFixtest',
              args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                    'isac_speech_and_misc_wb.pcm'],
              revision=revision,
              perf_test=True)
          self.virtual_webcam_check()
          self.add_test(
              'libjingle_peerconnection_java_unittest',
              env={'LD_PRELOAD': '/usr/lib/x86_64-linux-gnu/libpulse.so.0'})

        self.virtual_webcam_check()
        self.add_test(
            'vie_auto_test',
            args=['--automated',
                  '--capture_test_ensure_resolution_alignment_in_capture_device='
                  'false'],
            revision=revision,
            perf_test=True)
        self.add_test('voe_auto_test', args=['--automated'])
        self.virtual_webcam_check()
        self.add_test('video_capture_tests')
        self.add_test('webrtc_perf_tests', revision=revision, perf_test=True)
      elif test_suite == 'chromium':
        # Many of these tests run in the Chromium WebRTC waterfalls are not run in
        # the main Chromium waterfalls as they are marked as MANUAL_. This is
        # because they rely on physical audio and video devices, which are only
        # available at bare-metal machines.
        self.add_test(
            'content_browsertests',
            args=['--gtest_filter=WebRtc*', '--run-manual',
                  '--test-launcher-print-test-stdio=always',
                  '--test-launcher-bot-mode'],
            revision=revision,
            perf_test=True)
        self.add_test(
            'browser_tests',
            # These tests needs --test-launcher-jobs=1 since some of them are
            # not able to run in parallel (due to the usage of the
            # peerconnection server).
            args = ['--gtest_filter=WebRtc*:TabCapture*',
                    '--run-manual', '--ui-test-action-max-timeout=300000',
                    '--test-launcher-jobs=1',
                    '--test-launcher-bot-mode',
                    '--test-launcher-print-test-stdio=always'],
            revision=revision,
            perf_test=True)
        self.add_test(
            'content_unittests',
            args=['--gtest_filter=WebRtc*:WebRTC*:RTC*:MediaStream*'])
      elif test_suite == 'android':
        self.m.chromium_android.common_tests_setup_steps()

        for test in sorted(self.ANDROID_APK_TESTS.keys()):
          # Add the filename of the test.isolate files to the path.
          isolate_file = self.m.path.join(self.ANDROID_APK_TESTS[test],
                                          '%s.isolate' % test)
          self.test_runner(test, isolate_file)

        self.m.chromium_android.logcat_dump()
        # Disable stack tools steps until crbug.com/411685 is fixed.
        #self.m.chromium_android.stack_tool_steps()
        self.m.chromium_android.test_report()

  @recipe_api.composite_step
  def add_test(self, test, name=None, args=None, revision=None, env=None,
               perf_test=False, perf_dashboard_id=None, parallel=False):
    """Helper function to invoke chromium.runtest().

    Notice that the name parameter should be the same as the test executable in
    order to get the stdio links in the perf dashboard to become correct.
    """
    name = name or test
    args = args or []
    env = env or {}
    if self.c.PERF_ID and perf_test:
      perf_dashboard_id = perf_dashboard_id or test
      assert revision, ('Revision must be specified for perf tests as they '
                        'upload data to the perf dashboard.')
      self.m.chromium.runtest(
          test=test, args=args, name=name,
          results_url=self.DASHBOARD_UPLOAD_URL, annotate='graphing',
          xvfb=True, perf_dashboard_id=perf_dashboard_id, test_type=test,
          env=env, revision=revision, perf_id=self.c.PERF_ID,
          perf_config=self.c.PERF_CONFIG)
    elif parallel:
      script = self.m.path['checkout'].join('third_party', 'gtest-parallel',
                                            'gtest-parallel')
      test_executable = self.m.chromium.c.build_dir.join(
          self.m.chromium.c.build_config_fs, test)
      self.m.python(name, script, args=[test_executable] + args, env=env)
    else:
      self.m.chromium.runtest(
          test=test, args=args, name=name, annotate='gtest', xvfb=True,
          test_type=test, env=env)

  @recipe_api.composite_step
  def test_runner(self, test, isolate_path):
    """Adds a test to run on Android devices.

    This is a minimal version for WebRTC, similar to the methods in the
    chromium_android recipe module. It's needed since we need to alter the
    environment.
    """
    script = self.m.path['checkout'].join('build', 'android', 'test_runner.py')
    args = ['gtest', '-s', test, '--verbose', '--isolate-file-path',
            isolate_path]
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      args.append('--release')
    env = {'CHECKOUT_SOURCE_ROOT': self.m.path['checkout']}
    self.m.python(test, script, args, env=env)

  def sizes(self, revision):
    # TODO(kjellander): Move this into a function of the chromium recipe
    # module instead.
    assert self.c.PERF_ID, ('You must specify PERF_ID for the builder that '
                            'runs the sizes step.')
    sizes_script = self.m.path['build'].join('scripts', 'slave', 'chromium',
                                             'sizes.py')
    args = ['--target', self.m.chromium.c.BUILD_CONFIG,
            '--platform', self.m.chromium.c.TARGET_PLATFORM]
    test_name = 'sizes'
    self.add_test(
        test=sizes_script,
        name=test_name,
        perf_dashboard_id=test_name,
        args=args,
        revision=revision,
        perf_test=True)

  def package_build(self, gs_url, revision):
    self.m.archive.zip_and_upload_build(
        'package build',
        self.m.chromium.c.build_config_fs,
        gs_url,
        build_revision=revision)

  def extract_build(self, gs_url, revision):
    # Ensure old build directory is not used is by removing it.
    self.m.path.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    self.m.archive.download_and_unzip_build(
        'extract build',
        self.m.chromium.c.build_config_fs,
        gs_url,
        build_revision=revision)

    if not self.m.properties.get('parent_got_revision'):
      raise self.m.step.StepFailure(
         'Testers cannot be forced without providing revision information.'
         'Please select a previous build and click [Rebuild] or force a build'
         'for a Builder instead (will trigger new runs for the testers).')

  def cleanup(self):
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()
    else:
      self.m.chromium.cleanup_temp()

  def virtual_webcam_check(self):
    self.m.python(
      'webcam_check',
      self.m.path['build'].join('scripts', 'slave', 'webrtc',
                                'ensure_webcam_is_running.py'))
