# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

import common

SIMPLE_TESTS_TO_RUN = [
  'content_gl_tests',
  'gl_tests',
  'angle_unittests'
]

SIMPLE_NON_OPEN_SOURCE_TESTS_TO_RUN = [
  'gles2_conform_test',
]

class GpuApi(recipe_api.RecipeApi):
  def setup(self):
    """Call this once before any of the other APIs in this module."""

    # These values may be replaced by external configuration later
    self._dashboard_upload_url = 'https://chromeperf.appspot.com'
    self._gs_bucket_name = 'chromium-gpu-archive'

    # The infrastructure team has recommended not to use git yet on the
    # bots, but it's useful -- even necessary -- when testing locally.
    # To use, pass "use_git=True" as an argument to run_recipe.py.
    self._use_git = self.m.properties.get('use_git', False)

    self._configuration = 'chromium'
    if self.m.gclient.is_blink_mode:
      self._configuration = 'blink'

    self.m.chromium.set_config(self._configuration, GIT_MODE=self._use_git)
    # This is needed to make GOMA work properly on Mac.
    if self.m.platform.is_mac:
      self.m.chromium.set_config(self._configuration + '_clang',
                                 GIT_MODE=self._use_git)
    self.m.gclient.apply_config('chrome_internal')
    if self.m.tryserver.is_tryserver:
      # Force dcheck on in try server builds.
      self.m.chromium.apply_config('dcheck')

    # Use the default Ash and Aura settings on all bots (specifically Blink
    # bots).
    self.m.chromium.c.gyp_env.GYP_DEFINES.pop('use_ash', None)
    self.m.chromium.c.gyp_env.GYP_DEFINES.pop('use_aura', None)

    # TODO(kbr): remove the workaround for http://crbug.com/328249 .
    # See crbug.com/335827 for background on the conditional.
    if not self.m.platform.is_win:
      self.m.chromium.c.gyp_env.GYP_DEFINES['disable_glibcxx_debug'] = 1

    # Don't skip the frame_rate data, as it's needed for the frame rate tests.
    # Per iannucci@, it can be relied upon that solutions[1] is src-internal.
    # Consider managing this in a 'gpu' config.
    del self.m.gclient.c.solutions[1].custom_deps[
        'src/chrome/test/data/perf/frame_rate/private']

    self.m.chromium.c.gyp_env.GYP_DEFINES['internal_gles2_conform_tests'] = 1

    # This recipe requires the use of isolates for running tests.
    self.m.isolate.set_isolate_environment(self.m.chromium.c)

    # The FYI waterfall is being used to test top-of-tree ANGLE with
    # Chromium on all platforms.
    if self.is_fyi_waterfall:
      self.m.gclient.c.solutions[0].custom_vars['angle_revision'] = (
          'refs/remotes/origin/master')

    # This is part of the workaround for flakiness during gclient
    # revert, below.
    # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
    self.m.step.auto_resolve_conflicts = True

  @property
  def _build_revision(self):
    """Returns the revision of the current build. The pixel and maps
    tests use this value when uploading error images to cloud storage,
    only for naming purposes. This could be changed to use a different
    identifier (for example, the build number on the slave), but using
    this value is convenient for easily identifying results."""
    # On the Blink bots, the 'revision' property alternates between a
    # Chromium and a Blink revision, so is not a good value to use.
    #
    # In all cases on the waterfall, the tester is triggered from a
    # builder which sends down parent_got_revision. The only situation
    # where this doesn't happen is when running the build_and_test
    # recipe locally for testing purposes.
    rev = self.m.properties.get('parent_got_revision')
    if rev:
      return rev
    # Fall back to querying the workspace as a last resort. This should
    # only be necessary on combined builder/testers, which isn't a
    # configuration which actually exists on any waterfall any more. If the
    # build_and_test recipe is being run locally and the checkout is being
    # skipped, then the 'parent_got_revision' property can be specified on
    # the command line as a workaround.
    update_step = self.m.step_history.get('gclient sync', None)
    if not update_step:
      update_step = self.m.step_history['bot_update']
    return update_step.presentation.properties['got_revision']

  @property
  def _webkit_revision(self):
    """Returns the webkit revision of the current build."""
    # In all cases on the waterfall, the tester is triggered from a
    # builder which sends down parent_got_webkit_revision. The only
    # situation where this doesn't happen is when running the
    # build_and_test recipe locally for testing purposes.
    wk_rev = self.m.properties.get('parent_got_webkit_revision')
    if wk_rev:
      return wk_rev
    # Fall back to querying the workspace as a last resort. This should
    # only be necessary on combined builder/testers, which isn't a
    # configuration which actually exists on any waterfall any more. If the
    # build_and_test recipe is being run locally and the checkout is being
    # skipped, then the 'parent_got_webkit_revision' property can be
    # specified on the command line as a workaround.
    update_step = self.m.step_history.get('gclient sync', None)
    if not update_step:
      update_step = self.m.step_history['bot_update']
    return update_step.presentation.properties['got_webkit_revision']

  @property
  def _master_class_name_for_testing(self):
    """Allows the class name of the build master to be mocked for
    local testing by setting the build property
    "master_class_name_for_testing" on the command line. The bots do
    not need to, and should not, set this property. Class names follow
    the naming convention like "ChromiumWebkit" and "ChromiumGPU".
    This value is used by the flakiness dashboard when uploading
    results. See the documentation of the --master-class-name argument
    to runtest.py for full documentation."""
    return self.m.properties.get('master_class_name_for_testing')

  @property
  def is_fyi_waterfall(self):
    """Indicates whether the recipe is running on the GPU FYI waterfall."""
    return self.m.properties['mastername'] == 'chromium.gpu.fyi'

  def checkout_steps(self):
    # Always force a gclient-revert in order to avoid problems when
    # directories are added to, removed from, and re-added to the repo.
    # crbug.com/329577
    yield self.m.bot_update.ensure_checkout()
    bot_update_mode = self.m.step_history.last_step().json.output['did_run']
    if not bot_update_mode:
      yield self.m.gclient.checkout(revert=True,
                                    can_fail_build=False,
                                    abort_on_failure=False)

      # Workaround for flakiness during gclient revert.
      if any(step.retcode != 0 for step in self.m.step_history.values()):
        # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
        yield (
          self.m.path.rmcontents('slave build directory',
                                self.m.path['slave_build']),
          self.m.gclient.checkout(),
        )

      # If being run as a try server, apply the CL.
      yield self.m.tryserver.maybe_apply_issue()

  def compile_steps(self):
    # We only need to runhooks if we're going to compile locally.
    yield self.m.chromium.runhooks()
    # Since performance tests aren't run on the debug builders, it isn't
    # necessary to build all of the targets there.
    build_tag = '' if self.m.chromium.is_release_build else 'debug_'
    # It's harmless to process the isolate-related targets even if they
    # aren't supported on the current configuration (because the component
    # build is used).
    is_tryserver = self.m.tryserver.is_tryserver
    targets=['chromium_gpu_%sbuilder' % build_tag] + [
      '%s_run' % test for test in common.GPU_ISOLATES]
    yield self.m.chromium.compile(
        targets=targets,
        name='compile',
        abort_on_failure=(not is_tryserver),
        can_fail_build=(not is_tryserver))
    if is_tryserver and self.m.step_history['compile'].retcode != 0:
      # crbug.com/368875: have seen situations where autogenerated
      # files aren't regenerated properly on the tryservers. Try a
      # clobber build before failing the job.
      yield self.m.chromium.compile(
        targets=targets,
        name='compile (clobber)',
        force_clobber=True)
    yield self.m.isolate.find_isolated_tests(
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs),
        common.GPU_ISOLATES)

  def test_steps(self):
    # TODO(kbr): currently some properties are passed to runtest.py via
    # factory_properties in the master.cfg: generate_gtest_json,
    # show_perf_results, test_results_server, and perf_id. runtest.py
    # should be modified to take these arguments on the command line,
    # and the setting of these properties should happen in this recipe
    # instead.

    # Note: we do not run the crash_service on Windows any more now
    # that these bots do not auto-reboot. There's no script which
    # tears it down, and the fact that it's live prevents new builds
    # from being unpacked correctly.

    # Until this is more fully tested, leave this cleanup step local
    # to the GPU recipe.
    if self.m.platform.is_linux:
      def ignore_failure(step_result):
        step_result.presentation.status = 'SUCCESS'
      yield self.m.step('killall gnome-keyring-daemon',
                        ['killall', '-9', 'gnome-keyring-daemon'],
                        followup_fn=ignore_failure,
                        can_fail_build=False)

    # Note: --no-xvfb is the default.
    # Copy the test list to avoid mutating it.
    basic_tests = list(SIMPLE_TESTS_TO_RUN)
    # Only run tests on the tree closers and on the CQ which are
    # available in the open-source repository.
    if self.is_fyi_waterfall:
      basic_tests += SIMPLE_NON_OPEN_SOURCE_TESTS_TO_RUN
    for test in basic_tests:
      yield self._run_isolate(test, args=['--use-gpu-in-tests'])

    # Google Maps Pixel tests.
    yield self._run_isolated_telemetry_gpu_test(
      'maps', name='maps_pixel_test',
      args=[
        '--build-revision',
        str(self._build_revision),
        '--test-machine-name',
        self.m.properties['buildername']
      ])

    # Pixel tests.
    # Try servers pull their results from cloud storage; the other
    # tester bots send their results to cloud storage.
    #
    # NOTE that ALL of the bots need to share a bucket. They can't be split
    # by mastername/waterfall, because the try servers are on a different
    # waterfall (tryserver.chromium) than the other test bots (chromium.gpu
    # and chromium.webkit, as of this writing). This means there will be
    # races between bots with identical OS/GPU combinations, on different
    # waterfalls, attempting to upload results for new versions of each
    # pixel test. If this is a significant problem in practice then we will
    # have to rethink the cloud storage code in the pixel tests.
    ref_img_arg = '--upload-refimg-to-cloud-storage'
    if self.m.tryserver.is_tryserver:
      ref_img_arg = '--download-refimg-from-cloud-storage'
    cloud_storage_bucket = 'chromium-gpu-archive/reference-images'
    yield self._run_isolated_telemetry_gpu_test('pixel',
        args=[
            '--build-revision',
            str(self._build_revision),
            ref_img_arg,
            '--refimg-cloud-storage-bucket',
            cloud_storage_bucket,
            '--os-type',
            self.m.chromium.c.TARGET_PLATFORM,
            '--test-machine-name',
            self.m.properties['buildername']
        ],
        name='pixel_test')

    # WebGL conformance tests.
    yield self._run_isolated_telemetry_gpu_test('webgl_conformance')

    # Context lost tests.
    yield self._run_isolated_telemetry_gpu_test('context_lost')

    # Memory tests.
    yield self._run_isolated_telemetry_gpu_test('memory_test')

    # Screenshot synchronization tests.
    yield self._run_isolated_telemetry_gpu_test('screenshot_sync')

    # Hardware acceleration tests.
    yield self._run_isolated_telemetry_gpu_test(
      'hardware_accelerated_feature')

    # GPU process launch tests.
    yield self._run_isolated_telemetry_gpu_test('gpu_process',
                                                name='gpu_process_launch')

    # Smoke test for gpu rasterization of web content.
    yield self._run_isolated_telemetry_gpu_test(
      'gpu_rasterization',
      args=[
        '--build-revision', str(self._build_revision),
        '--test-machine-name', self.m.properties['buildername']
      ])

    # Tab capture end-to-end (correctness) tests.
    yield self._run_isolate(
        'tab_capture_end2end_tests',
        name='tab_capture_end2end_tests',
        spawn_dbus=True)

    # TODO(kbr): after the conversion to recipes, add all GPU related
    # steps from the main waterfall, like gpu_unittests.

  def _run_isolate(self, test, isolate_name=None, **kwargs):
    test_name = isolate_name or test
    # The test_type must end in 'test' or 'tests' in order for the results to
    # automatically show up on the flakiness dashboard.
    #
    # Currently all tests on the GPU bots follow this rule, so we can't add
    # code like in chromium/api.py, run_telemetry_test.
    assert test_name.endswith('test') or test_name.endswith('tests')
    # TODO(kbr): turn this into a temporary path. There were problems
    # with the recipe simulation test in doing so and cleaning it up.
    results_directory = self.m.path['slave_build'].join(
      'gtest-results', test_name)
    yield self.m.isolate.runtest(
      isolate_name or test,
      self._build_revision,
      self._webkit_revision,
      annotate='gtest',
      test_type=test_name,
      generate_json_file=True,
      results_directory=results_directory,
      master_class_name=self._master_class_name_for_testing,
      **kwargs)

  def _run_isolated_telemetry_gpu_test(self, test, args=None, name=None,
                                       **kwargs):
    test_args = ['-v', '--use-devtools-active-port']
    if args:
      test_args.extend(args)
    yield self.m.isolate.run_telemetry_test(
      'telemetry_gpu_test',
      test,
      self._build_revision,
      self._webkit_revision,
      args=test_args,
      name=name,
      master_class_name=self._master_class_name_for_testing,
      spawn_dbus=True,
      **kwargs)
