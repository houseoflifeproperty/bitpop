# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from slave import recipe_api


# Different types of builds this recipe module can do.
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
  'chromium_asan': {
    'chromium_config': 'chromium_asan',
    'gclient_config': 'chromium',
  },
  'chromium_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chrome_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos', 'chrome_internal'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium_chromeos_ozone': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos', 'ozone'],
    'gclient_config': 'chromium',
  },
  'chromium_chromeos_clang': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_ios_device': {
    'chromium_config': 'chromium_ios_device',
    'gclient_config': 'ios',
  },
  'chromium_ios_ninja': {
    'chromium_config': 'chromium_ios_ninja',
    'gclient_config': 'ios',
  },
  'chromium_ios_simulator': {
    'chromium_config': 'chromium_ios_simulator',
    'gclient_config': 'ios',
  },
  'chromium_no_goma': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
  },
  'chromium_oilpan': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['oilpan'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium_v8': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'gclient_apply_config': [
      'v8_bleeding_edge_git',
      'chromium_lkcr',
      'show_v8_revision',
    ],
  },
  'chromium_skia': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium_skia',
  },
  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'perf': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'perf',
  }
}


class ChromiumTestsApi(recipe_api.RecipeApi):
  def sync_and_configure_build(self, mastername, buildername,
                               override_bot_type=None, enable_swarming=False):
    # Make an independent copy so that we don't overwrite global state
    # with updates made dynamically based on the test specs.
    master_dict = copy.deepcopy(self.m.chromium.builders.get(mastername, {}))

    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})
    recipe_config_name = bot_config['recipe_config']
    assert recipe_config_name, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))
    recipe_config = RECIPE_CONFIGS[recipe_config_name]

    self.m.chromium.set_config(
        recipe_config['chromium_config'],
        **bot_config.get('chromium_config_kwargs', {}))
    # Set GYP_DEFINES explicitly because chromium config constructor does
    # not support that.
    self.m.chromium.c.gyp_env.GYP_DEFINES.update(
        bot_config.get('GYP_DEFINES', {}))
    if bot_config.get('use_isolate'):
      self.m.isolate.set_isolate_environment(self.m.chromium.c)
    for c in recipe_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    self.m.gclient.set_config(
        recipe_config['gclient_config'],
        **bot_config.get('gclient_config_kwargs', {}))
    for c in recipe_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)

    if 'android_config' in bot_config:
      self.m.chromium_android.set_config(
          bot_config['android_config'],
          **bot_config.get('chromium_config_kwargs', {}))

    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    if bot_config.get('set_component_rev'):
      # If this is a component build and the main revision is e.g. blink,
      # webrtc, or v8, the custom deps revision of this component must be
      # dynamically set to either:
      # (1) the revision of the builder if this is a tester,
      # (2) 'revision' from the waterfall, or
      # (3) 'HEAD' for forced builds with unspecified 'revision'.
      # TODO(machenbach): Use parent_got_cr_revision on testers with component
      # builds to match also the chromium revision from the builder.
      component_rev = self.m.properties.get('revision', 'HEAD')
      if bot_type == 'tester':
        component_rev = self.m.properties.get(
            'parent_got_revision', component_rev)
      dep = bot_config.get('set_component_rev')
      self.m.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

    if self.m.platform.is_win:
      self.m.chromium.taskkill()

    # Bot Update re-uses the gclient configs.
    update_step = self.m.bot_update.ensure_checkout()
    assert update_step.json.output['did_run']
    # HACK(dnj): Remove after 'crbug.com/398105' has landed
    self.m.chromium.set_build_properties(update_step.json.output['properties'])

    if not enable_swarming:
      enable_swarming = bot_config.get('enable_swarming')

    if enable_swarming:
      self.m.isolate.set_isolate_environment(self.m.chromium.c)
      self.m.swarming.check_client_version()
      self.m.swarming.task_priority = 50

    if not bot_config.get('disable_runhooks'):
      self.m.chromium.runhooks(env=bot_config.get('runhooks_env', {}))

    test_spec_file = bot_config.get('testing', {}).get('test_spec_file',
                                                       '%s.json' % mastername)
    test_spec_path = self.m.path['checkout'].join('testing', 'buildbot',
                                               test_spec_file)
    # TODO(phajdan.jr): Bots should have no generators instead.
    if bot_config.get('disable_tests'):
      test_spec = {}
    else:
      test_spec_result = self.m.json.read(
          'read test spec',
          test_spec_path,
          step_test_data=lambda: self.m.json.test_api.output({}))
      test_spec_result.presentation.step_text = 'path: %s' % test_spec_path
      test_spec = test_spec_result.json.output

    for loop_buildername, builder_dict in master_dict.get(
        'builders', {}).iteritems():
      builder_dict.setdefault('tests', [])
      for generator in builder_dict.get('test_generators', []):
        builder_dict['tests'] = (
            list(generator(self.m, mastername, loop_buildername, test_spec,
                           enable_swarming=enable_swarming)) +
            builder_dict['tests'])

    return update_step, master_dict, test_spec

  def compile(self, mastername, buildername, update_step, master_dict,
              test_spec, override_bot_type=None, override_tests=None):
    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})
    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    tests = bot_config.get('tests', [])
    if override_tests is not None:
      tests = override_tests

    self.m.chromium.cleanup_temp()
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.clean_local_files()

    if bot_type in ['builder', 'builder_tester']:
      compile_targets = set(bot_config.get('compile_targets', []))
      tests_including_triggered = tests[:]
      for loop_buildername, builder_dict in master_dict.get(
          'builders', {}).iteritems():
        if builder_dict.get('parent_buildername') == buildername:
          for test in builder_dict.get('tests', []):
            tests_including_triggered.append(test)

      for t in tests_including_triggered:
        compile_targets.update(t.compile_targets(self.m))

      self.m.chromium.compile(targets=sorted(compile_targets))
      self.m.chromium.checkdeps()

      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        self.m.chromium_android.check_webview_licenses()
        self.m.chromium_android.findbugs()

      isolated_targets = [
        t.name for t in tests_including_triggered if t.uses_swarming
      ]
      if isolated_targets:
        self.m.isolate.find_isolated_tests(
            self.m.chromium.output_dir, targets=list(set(isolated_targets)))

    got_revision = update_step.presentation.properties['got_revision']

    if bot_type == 'builder':
      if mastername == 'chromium.linux':
        # TODO(samuong): This is restricted to Linux for now until I have more
        # confidence that it is not totally broken.
        self.m.archive.archive_dependencies(
            'archive dependencies',
            self.m.chromium.c.build_config_fs,
            mastername,
            buildername,
            self.m.properties.get('buildnumber'))
      self.m.archive.zip_and_upload_build(
          'package build',
          self.m.chromium.c.build_config_fs,
          self.m.archive.legacy_upload_url(
              master_config.get('build_gs_bucket'),
              extra_url_components=(None if mastername == 'chromium.perf' else
                                    self.m.properties['mastername'])),
          build_revision=got_revision,
          cros_board=self.m.chromium.c.TARGET_CROS_BOARD,
      )

  def tests_for_builder(self, mastername, buildername, update_step, master_dict,
                        override_bot_type=None):
    got_revision = update_step.presentation.properties['got_revision']

    bot_config = master_dict.get('builders', {}).get(buildername)
    master_config = master_dict.get('settings', {})

    bot_type = override_bot_type or bot_config.get('bot_type', 'builder_tester')

    if bot_type == 'tester':
      # Protect against hard to debug mismatches between directory names
      # used to run tests from and extract build to. We've had several cases
      # where a stale build directory was used on a tester, and the extracted
      # build was not used at all, leading to confusion why source code changes
      # are not taking effect.
      #
      # The best way to ensure the old build directory is not used is to
      # remove it.
      self.m.path.rmtree(
        'build directory',
        self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))
      self.m.archive.download_and_unzip_build(
        'extract build',
        self.m.chromium.c.build_config_fs,
        self.m.archive.legacy_download_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=(None if mastername == 'chromium.perf' else
           self.m.properties['mastername'])),
        build_revision=self.m.properties.get(
          'parent_got_revision', got_revision),
        build_archive_url=self.m.properties.get('parent_build_archive_url'),
        )

    tests = bot_config.get('tests', [])

    # TODO(phajdan.jr): bots should just leave tests empty instead of this.
    if bot_config.get('do_not_run_tests'):
      tests = []

    return tests

  def setup_chromium_tests(self, test_runner):
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.common_tests_setup_steps()

    if self.m.platform.is_win:
      self.m.chromium.crash_handler()

    try:
      return test_runner()
    finally:
      if self.m.platform.is_win:
        self.m.chromium.process_dumps()

      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        self.m.chromium_android.common_tests_final_steps()
