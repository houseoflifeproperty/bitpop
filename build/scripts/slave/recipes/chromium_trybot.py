# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'itertools',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'step',
  'step_history',
  'test_utils',
  'tryserver',
]


BUILDERS = {
  'tryserver.chromium': {
    'builders': {
      'linux_chromium_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_rel_alt': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_clang_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_clang',
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_clang_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_clang',
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_chromeos',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_chromeos',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_clang_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_chromeos_clang',
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_clang_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_chromeos_clang',
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty32_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_trusty32_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'mac_chromium_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_chromium_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'win_chromium_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_x64_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_chromium_x64_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
}


def GenSteps(api):
  class CheckdepsTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'checkdeps'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      return api.chromium.checkdeps(suffix, can_fail_build=False)

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      results = api.step_history[self._step_name(suffix)].json.output
      result_set = set()
      for result in results:
        for violation in result['violations']:
          result_set.add((result['dependee_path'], violation['include_path']))
      return ['%s: %s' % (r[0], r[1]) for r in result_set]


  class Deps2GitTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'deps2git'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      yield (
        api.chromium.deps2git(suffix, can_fail_build=False),
        api.chromium.deps2submodules()
      )

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output


  class GTestTest(api.test_utils.Test):
    def __init__(self, name, args=None):
      api.test_utils.Test.__init__(self)
      self._name = name
      self._args = args or []

    @property
    def name(self):
      return self._name

    def compile_targets(self):
      return [self.name]

    def run(self, suffix):
      def followup_fn(step_result):
        r = step_result.json.gtest_results
        p = step_result.presentation

        if r.valid:
          p.step_text += api.test_utils.format_step_text([
              ['failures:', r.failures]
          ])

      # Copy the list because run can be invoked multiple times and we modify
      # the local copy.
      args = self._args[:]

      if suffix == 'without patch':
        args.append(api.chromium.test_launcher_filter(
                        self.failures('with patch')))

      return api.chromium.runtest(
          self.name,
          args,
          annotate='gtest',
          test_launcher_summary_output=api.json.gtest_results(
              add_json_log=False),
          xvfb=True,
          name=self._step_name(suffix),
          parallel=True,
          can_fail_build=False,
          followup_fn=followup_fn,
          step_test_data=lambda: api.json.test_api.canned_gtest_output(True))

    def has_valid_results(self, suffix):
      step_name = self._step_name(suffix)
      gtest_results = api.step_history[step_name].json.gtest_results
      if not gtest_results.valid:  # pragma: no cover
        return False
      global_tags = gtest_results.raw.get('global_tags', [])
      return 'UNRELIABLE_RESULTS' not in global_tags


    def failures(self, suffix):
      step_name = self._step_name(suffix)
      return api.step_history[step_name].json.gtest_results.failures


  class NaclIntegrationTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'nacl_integration'

    @staticmethod
    def compile_targets():
      return ['chrome']

    def run(self, suffix):
      args = [
        '--mode', api.chromium.c.build_config_fs,
        '--json_build_results_output_file', api.json.output(),
      ]
      return api.python(
          self._step_name(suffix),
          api.path['checkout'].join('chrome',
                            'test',
                            'nacl_test_injection',
                            'buildbot_nacl_integration.py'),
          args,
          can_fail_build=False,
          step_test_data=lambda: api.m.json.test_api.output([]))

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      failures = api.step_history[self._step_name(suffix)].json.output
      return [f['raw_name'] for f in failures]

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))

  # Make sure tests and the recipe specify correct and matching platform.
  assert api.platform.name == bot_config.get('testing', {}).get('platform')

  api.chromium.set_config(bot_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('chromium')
  api.step.auto_resolve_conflicts = True

  yield api.bot_update.ensure_checkout()
  # The first time we run bot update, remember if bot_update mode is on or off.
  bot_update_mode = api.step_history.last_step().json.output['did_run']
  if not bot_update_mode:
    yield api.gclient.checkout(
        revert=True, can_fail_build=False, abort_on_failure=False)
    for step in api.step_history.values():
      if step.retcode != 0:
        if api.platform.is_win:
          yield api.chromium.taskkill()
        yield (
          api.path.rmcontents('slave build directory',
                              api.path['slave_build']),
          api.gclient.checkout(revert=False),
        )
        break
    yield api.tryserver.maybe_apply_issue()

  yield api.json.read(
      'read test spec',
      api.path['checkout'].join('testing',
                                'buildbot',
                                'chromium_trybot.json'),
      step_test_data=lambda: api.json.test_api.output([
        'base_unittests',
        {
          'test': 'mojo_common_unittests',
          'platforms': ['linux', 'mac'],
        },
        {
          'test': 'sandbox_linux_unittests',
          'platforms': ['linux'],
          'chromium_configs': ['chromium_chromeos', 'chromium_chromeos_clang'],
          'args': ['--test-launcher-print-test-stdio=always'],
        },
        {
          'test': 'browser_tests',
          'exclude_builders': ['tryserver.chromium:win_chromium_x64_rel'],
        },
      ]))

  yield api.chromium.runhooks(abort_on_failure=False, can_fail_build=False)
  if api.step_history.last_step().retcode != 0:
    # Before removing the checkout directory try just using LKCR.
    api.gclient.set_config('chromium_lkcr')

    # Since we're likely to switch to an earlier revision, revert the patch,
    # sync with the new config, and apply issue again.
    if bot_update_mode:
      # TODO(hinoka): Once lkcr exists and is a tag, it should just be lkcr
      #               rather than origin/lkcr.
      yield api.bot_update.ensure_checkout(ref='origin/lkcr', suffix='lkcr')
      yield api.chromium.runhooks()
    else:
      yield api.gclient.checkout(revert=True)
      yield api.tryserver.maybe_apply_issue()

      yield api.chromium.runhooks(abort_on_failure=False, can_fail_build=False)
      if api.step_history.last_step().retcode != 0:
        if api.platform.is_win:
          yield api.chromium.taskkill()
        yield (
          api.path.rmcontents('slave build directory', api.path['slave_build']),
          api.gclient.checkout(revert=False),
          api.tryserver.maybe_apply_issue(),
          api.chromium.runhooks()
        )

  gtest_tests = []

  test_spec = api.step_history['read test spec'].json.output
  for test in test_spec:
    test_name = None
    test_args = None

    if isinstance(test, unicode):
      test_name = test.encode('utf-8')
    elif isinstance(test, dict):
      if 'platforms' in test:
        if api.platform.name not in test['platforms']:
          continue

      if 'chromium_configs' in test:
        if bot_config['chromium_config'] not in test['chromium_configs']:
          continue

      if 'exclude_builders' in test:
        if '%s:%s' % (mastername, buildername) in test['exclude_builders']:
          continue

      test_args = test.get('args')

      if 'test' not in test:  # pragma: no cover
        raise ValueError('Invalid entry in test spec: %r' % test)

      test_name = test['test'].encode('utf-8')
    else:  # pragma: no cover
      raise ValueError('Unrecognized entry in test spec: %r' % test)

    if test_name:
      gtest_tests.append(GTestTest(test_name, test_args))

  tests = []
  tests.append(CheckdepsTest())
  tests.append(Deps2GitTest())
  for test in gtest_tests:
    tests.append(test)
  tests.append(NaclIntegrationTest())

  compile_targets = list(api.itertools.chain(
      *[t.compile_targets() for t in tests]))
  # TODO(phajdan.jr): Also compile 'all' on win, http://crbug.com/368831 .
  # Disabled for now because it takes too long and/or fails on Windows.
  if not api.platform.is_win:
    compile_targets = ['all'] + compile_targets
  yield api.chromium.compile(compile_targets,
                             name='compile (with patch)',
                             abort_on_failure=False,
                             can_fail_build=False)
  if api.step_history['compile (with patch)'].retcode != 0:
    # Only use LKCR when compile fails. Note that requested specific revision
    # can still override this.
    api.gclient.set_config('chromium_lkcr')

    # Since we're likely to switch to an earlier revision, revert the patch,
    # sync with the new config, and apply issue again.
    if bot_update_mode:
      yield api.bot_update.ensure_checkout(ref='origin/lkcr',
                                           suffix='lkcr clobber')
      yield api.chromium.runhooks()
    else:
      yield api.gclient.checkout(revert=True)
      yield api.tryserver.maybe_apply_issue()

    yield api.chromium.compile(compile_targets,
                               name='compile (with patch, lkcr, clobber)',
                               force_clobber=True,
                               abort_on_failure=False,
                               can_fail_build=False)
    if api.step_history['compile (with patch, lkcr, clobber)'].retcode != 0:
      if api.platform.is_win:
        yield api.chromium.taskkill()
      yield api.path.rmcontents('slave build directory',
                                api.path['slave_build']),
      if bot_update_mode:
        yield api.bot_update.ensure_checkout(ref='origin/lkcr',
                                             suffix='lkcr clobber nuke')
      else:
        yield api.gclient.checkout(revert=False)
        yield api.tryserver.maybe_apply_issue()

      yield api.chromium.runhooks()
      yield api.chromium.compile(compile_targets,
                                 name='compile '
                                      '(with patch, lkcr, clobber, nuke)',
                                 force_clobber=True)

  # Do not run tests if the build is already in a failed state.
  if api.step_history.failed:
    return

  if bot_config['compile_only']:
    return

  # TODO(phajdan.jr): Make it possible to retry telemetry tests (add JSON).
  yield (
    api.chromium.run_telemetry_unittests(),
    api.chromium.run_telemetry_perf_unittests(),
  )

  def deapply_patch_fn(failing_tests):
    if api.platform.is_win:
      yield api.chromium.taskkill()
    if bot_update_mode:
      yield api.bot_update.ensure_checkout(patch=False,
                                           always_run=True,
                                           update_presentation=False)
    else:
      yield api.gclient.checkout(revert=True, always_run=True),
    yield api.chromium.runhooks(always_run=True),
    compile_targets = list(api.itertools.chain(
                               *[t.compile_targets() for t in failing_tests]))
    if compile_targets:
      yield api.chromium.compile(compile_targets,
                                 name='compile (without patch)',
                                 abort_on_failure=False,
                                 can_fail_build=False,
                                 always_run=True)
      if api.step_history['compile (without patch)'].retcode != 0:
        yield api.chromium.compile(compile_targets,
                                   name='compile (without patch, clobber)',
                                   force_clobber=True,
                                   always_run=True)

  yield api.test_utils.determine_new_failures(tests, deapply_patch_fn)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_checkdeps = {
    True: [],
    False: [
      {
        'dependee_path': '/path/to/dependee',
        'violations': [
          { 'include_path': '/path/to/include', },
        ],
      },
    ],
  }
  canned_test = api.json.canned_gtest_output
  def props(config='Release', mastername='tryserver.chromium',
            buildername='linux_chromium_rel', **kwargs):
    kwargs.setdefault('revision', None)
    return api.properties.tryserver(
      build_config=config,
      mastername=mastername,
      buildername=buildername,
      **kwargs
    )

  yield (api.test('linux_rel_alt') +
         api.properties(mastername='tryserver.chromium',
                        buildername='linux_rel_alt',
                        slavename='slave101-c4'))

  # While not strictly required for coverage, record expectations for each
  # of the configs so we can see when and how they change.
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                  _sanitize_nonalpha(buildername))
      yield (
        api.test(test_name) +
        api.platform(bot_config['testing']['platform'],
                     bot_config.get(
                         'chromium_config_kwargs', {}).get('TARGET_BITS', 64)) +
        props(mastername=mastername, buildername=buildername)
      )

  # It is important that even when steps related to deapplying the patch
  # fail, we either print the summary for all retried steps or do no
  # retries at all.
  yield (
    api.test('persistent_failure_and_runhooks_2_fail_test') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           canned_test(passing=False)) +
    api.step_data('gclient runhooks (2)', retcode=1)
  )

  yield (
    api.test('persistent_failure_and_runhooks_2_fail_test_bot_update') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           canned_test(passing=False)) +
    api.step_data('gclient runhooks (2)', retcode=1) +
    api.properties(mastername='tryserver.chromium',
                   buildername='linux_rel_alt',
                   slavename='slave101-c4')
  )

  yield (
    api.test('invalid_json_without_patch') +
    props(buildername='win_chromium_rel') +
    api.platform.name('win') +
    api.override_step_data('checkdeps (with patch)',
                           api.json.output(canned_checkdeps[False])) +
    api.override_step_data('checkdeps (without patch)',
                           api.json.output(None))
  )

  yield (
    api.test('gclient_runhooks_failure_bot_update') +
    props() +
    api.platform.name('linux') +
    api.step_data('gclient runhooks', retcode=1) +
    api.properties(mastername='tryserver.chromium',
                   buildername='linux_rel_alt',
                   slavename='slave101-c4')
  )

  for step in ('gclient revert', 'gclient runhooks'):
    yield (
      api.test(step.replace(' ', '_') + '_failure') +
      props(buildername='win_chromium_rel') +
      api.platform.name('win') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('gclient_revert_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.step_data('gclient runhooks', retcode=1) +
    api.step_data('gclient runhooks (2)', retcode=1) +
    api.step_data('gclient runhooks (3)', retcode=1)
  )

  yield (
    api.test('gclient_revert_failure_win') +
    props(buildername='win_chromium_rel') +
    api.platform.name('win') +
    api.step_data('gclient runhooks', retcode=1) +
    api.step_data('gclient runhooks (2)', retcode=1) +
    api.step_data('gclient runhooks (3)', retcode=1)
  )

  yield (
    api.test('gclient_sync_no_data') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('gclient sync', api.json.output(None))
  )

  yield (
    api.test('gclient_revert_nuke') +
    props() +
    api.platform.name('linux') +
    api.step_data('gclient revert', retcode=1)
  )

  yield (
    api.test('compile_failure') +
    props(buildername='win_chromium_rel') +
    api.platform.name('win') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber, nuke)', retcode=1)
  )

  yield (
    api.test('compile_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber, nuke)', retcode=1)
  )

  yield (
    api.test('compile_first_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber)', retcode=0)
  )

  yield (
    api.test('compile_failure_linux_bot_update') +
    props() +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber)', retcode=1) +
    api.step_data('compile (with patch, lkcr, clobber, nuke)', retcode=1) +
    api.properties(mastername='tryserver.chromium',
                   buildername='linux_rel_alt',
                   slavename='slave101-c4')
  )

  yield (
    api.test('deapply_compile_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.step_data('compile (without patch)', retcode=1)
  )
