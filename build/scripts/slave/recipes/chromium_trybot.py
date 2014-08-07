# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'isolate',
  'itertools',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'step',
  'step_history',
  'swarming',
  'test_utils',
  'tryserver',
]


BUILDERS = {
  'tryserver.chromium': {
    'builders': {
      'linux_arm_cross_compile': {
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
        'compile_only': True,
        'exclude_compile_all': True,
        'testing': {
          'platform': 'linux',
          'test_spec_file': 'chromium_arm.json',
        },
        'use_isolate': True,
      },
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
      # Fake builder to provide testing coverage for non-bot_update.
      'linux_no_bot_update': {
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
      'win8_chromium_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
          'test_spec_file': 'chromium_win8_trybot.json',
        },
      },
      'win8_chromium_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'chromium_config': 'chromium',
        'compile_only': False,
        'testing': {
          'platform': 'win',
          'test_spec_file': 'chromium_win8_trybot.json',
        },
      },
      # Fake builder to provide testing coverage for non-bot_update.
      'win_no_bot_update': {
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
    },
  },
}


def add_swarming_builder(original, swarming, server='tryserver.chromium'):
  """Duplicates builder config on |server|, adding 'enable_swarming: True'."""
  assert server in BUILDERS
  assert original in BUILDERS[server]['builders']
  assert swarming not in BUILDERS[server]['builders']
  conf = BUILDERS[server]['builders'][original].copy()
  conf['enable_swarming'] = True
  BUILDERS[server]['builders'][swarming] = conf


add_swarming_builder('linux_chromium_rel', 'linux_chromium_rel_swarming')
add_swarming_builder('win_chromium_rel', 'win_chromium_rel_swarming')
add_swarming_builder('mac_chromium_rel', 'mac_chromium_rel_swarming')


def GenSteps(api):
  class CheckdepsTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'checkdeps'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      return api.chromium.checkdeps(
          suffix, can_fail_build=False, always_run=True)

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      results = api.step_history[self._step_name(suffix)].json.output
      result_set = set()
      for result in results:
        for violation in result['violations']:
          result_set.add((result['dependee_path'], violation['include_path']))
      return ['%s: %s' % (r[0], r[1]) for r in result_set]


  class CheckpermsTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'checkperms'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      return api.chromium.checkperms(
          suffix, can_fail_build=False, always_run=True)

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      results = api.step_history[self._step_name(suffix)].json.output
      result_set = set()
      for result in results:
        result_set.add((result['rel_path'], result['error']))
      return ['%s: %s' % (r[0], r[1]) for r in result_set]


  class ChecklicensesTest(api.test_utils.Test):  # pylint: disable=W0232
    name = 'checklicenses'

    @staticmethod
    def compile_targets():
      return []

    @staticmethod
    def run(suffix):
      return api.chromium.checklicenses(
          suffix, can_fail_build=False, always_run=True)

    def has_valid_results(self, suffix):
      return api.step_history[self._step_name(suffix)].json.output is not None

    def failures(self, suffix):
      results = api.step_history[self._step_name(suffix)].json.output
      result_set = set()
      for result in results:
        result_set.add((result['filename'], result['license']))
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
    def __init__(self, name, args=None, compile_targets=None):
      api.test_utils.Test.__init__(self)
      self._name = name
      self._args = args or []

    @property
    def name(self):
      return self._name

    def compile_targets(self):
      return [self._name]

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


  class SwarmingGTestTest(api.test_utils.Test):
    def __init__(self, name, args=None, shards=1):
      api.test_utils.Test.__init__(self)
      self._name = name
      self._args = args or []
      self._shards = shards
      self._tasks = {}
      self._results = {}

    @property
    def name(self):
      return self._name

    def compile_targets(self):
      # <X>_run target depends on <X>, and then isolates it invoking isolate.py.
      # It is a convention, not a hard coded rule.
      return [self._name + '_run']

    def pre_run(self, suffix):
      """Launches the test on Swarming."""
      assert suffix not in self._tasks, (
          'Test %s was already triggered' % self._step_name(suffix))

      # *.isolated may be missing if *_run target is misconfigured. It's a error
      # in gyp, not a recipe failure. So carry on with recipe execution.
      isolated_hash = api.isolate.isolated_tests.get(self._name)
      if not isolated_hash:
        return api.python.inline(
            '[error] %s' % self._step_name(suffix),
            r"""
            import sys
            print '*.isolated file for target %s is missing' % sys.argv[1]
            sys.exit(1)
            """,
            args=[self._name],
            always_run=True)

      # If rerunning without a patch, run only tests that failed.
      args = self._args[:]
      if suffix == 'without patch':
        failed_tests = sorted(self.failures('with patch'))
        args.append('--gtest_filter=%s' % ':'.join(failed_tests))

      # Trigger the test on swarming.
      self._tasks[suffix] = api.swarming.gtest_task(
          title=self._step_name(suffix),
          isolated_hash=isolated_hash,
          shards=self._shards,
          test_launcher_summary_output=api.json.gtest_results(
              add_json_log=False),
          extra_args=args)
      return api.swarming.trigger([self._tasks[suffix]], always_run=True)

    def run(self, suffix):  # pylint: disable=R0201
      """Not used. All logic in pre_run, post_run."""
      return []

    def post_run(self, suffix):
      """Waits for launched test to finish and collect the results."""
      assert suffix not in self._results, (
          'Results of %s were already collected' % self._step_name(suffix))

      # Emit error if test wasn't triggered. This happens if *.isolated is not
      # found. (The build is already red by this moment anyway).
      if suffix not in self._tasks:
        return api.python.inline(
            '[collect error] %s' % self._step_name(suffix),
            r"""
            import sys
            print '%s wasn\'t triggered' % sys.argv[1]
            sys.exit(1)
            """,
            args=[self._name],
            always_run=True)

      # Update step presentation, store step results in self._results.
      def followup_fn(step_result):
        r = step_result.json.gtest_results
        p = step_result.presentation
        if r.valid:
          p.step_text += api.test_utils.format_step_text([
              ['failures:', r.failures]
          ])
        self._results[suffix] = r

      # Wait for test on swarming to finish. If swarming infrastructure is
      # having issues, this step produces no valid *.json test summary, and
      # 'has_valid_results' returns False.
      return api.swarming.collect(
          [self._tasks[suffix]],
          always_run=True,
          can_fail_build=False,
          followup_fn=followup_fn)

    def has_valid_results(self, suffix):
      # Test wasn't triggered or wasn't collected.
      if suffix not in self._tasks or not suffix in self._results:
        return False
      # Test ran, but failed to produce valid *.json.
      gtest_results = self._results[suffix]
      if not gtest_results.valid:  # pragma: no cover
        return False
      global_tags = gtest_results.raw.get('global_tags', [])
      return 'UNRELIABLE_RESULTS' not in global_tags

    def failures(self, suffix):
      assert self.has_valid_results(suffix)
      return self._results[suffix].failures


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


  def parse_test_spec(test_spec, enable_swarming, should_use_test):
    """Returns a list of tests to run and additional targets to compile.

    Uses 'should_use_test' callback to figure out what tests should be skipped.

    Returns triple (compile_targets, gtest_tests, swarming_tests) where
      gtest_tests is a list of GTestTest
      swarming_tests is a list of SwarmingGTestTest.
    """
    compile_targets = []
    gtest_tests_spec = []
    if isinstance(test_spec, dict):
      compile_targets = test_spec.get('compile_targets', [])
      gtest_tests_spec = test_spec.get('gtest_tests', [])
    else:
      # TODO(nodir): Remove this after
      # https://codereview.chromium.org/297303012/#ps50001
      # lands.
      gtest_tests_spec = test_spec

    gtest_tests = []
    swarming_tests = []
    for test in gtest_tests_spec:
      test_name = None
      test_dict = None

      # Read test_dict for the test, it defines where test can run.
      if isinstance(test, unicode):
        test_name = test.encode('utf-8')
        test_dict = {}
      elif isinstance(test, dict):
        if 'test' not in test:  # pragma: no cover
          raise ValueError('Invalid entry in test spec: %r' % test)
        test_name = test['test'].encode('utf-8')
        test_dict = test
      else:  # pragma: no cover
        raise ValueError('Unrecognized entry in test spec: %r' % test)

      # Should skip it completely?
      if not test_name or not should_use_test(test_dict):
        continue

      # If test can run on swarming, test_dict has a section that defines when
      # swarming should be used, in same format as main test dict.
      use_swarming = False
      swarming_shards = 1
      if enable_swarming:
        swarming_spec = test_dict.get('swarming') or {}
        if not isinstance(swarming_spec, dict):  # pragma: no cover
          raise ValueError('\'swarming\' entry in test spec should be a dict')
        if swarming_spec.get('can_use_on_swarming_builders'):
          use_swarming = should_use_test(swarming_spec)
        swarming_shards = swarming_spec.get('shards', 1)

      test_args = test_dict.get('args')
      if isinstance(test_args, basestring):
        test_args = [test_args]

      if use_swarming:
        swarming_tests.append(
            SwarmingGTestTest(test_name, test_args, swarming_shards))
      else:
        gtest_tests.append(GTestTest(test_name, test_args))

    return compile_targets, gtest_tests, swarming_tests


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
  # Settings GYP_DEFINES explicitly because chromium config constructor does
  # not support that.
  api.chromium.c.gyp_env.GYP_DEFINES.update(bot_config.get('GYP_DEFINES', {}))
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('chromium')
  api.step.auto_resolve_conflicts = True

  yield api.bot_update.ensure_checkout(force=True)

  test_spec_file = bot_config['testing'].get('test_spec_file',
                                             'chromium_trybot.json')
  test_spec_path = api.path.join('testing', 'buildbot', test_spec_file)
  def test_spec_followup_fn(step_result):
    step_result.presentation.step_text = 'path: %s' % test_spec_path
  yield api.json.read(
      'read test spec',
      api.path['checkout'].join(test_spec_path),
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
      ]),
      followup_fn=test_spec_followup_fn,
  )

  def should_use_test(test):
    """Given a test dict from test spec returns True or False."""
    if 'platforms' in test:
      if api.platform.name not in test['platforms']:
        return False
    if 'chromium_configs' in test:
      if bot_config['chromium_config'] not in test['chromium_configs']:
        return False
    if 'exclude_builders' in test:
      if '%s:%s' % (mastername, buildername) in test['exclude_builders']:
        return False
    return True

  # Parse test spec file into list of Test instances.
  compile_targets, gtest_tests, swarming_tests = parse_test_spec(
      api.step_history['read test spec'].json.output,
      bot_config.get('enable_swarming'),
      should_use_test)

  # Swarming uses Isolate to transfer files to swarming bots.
  # set_isolate_environment modifies GYP_DEFINES to enable test isolation.
  if bot_config.get('use_isolate') or swarming_tests:
    api.isolate.set_isolate_environment(api.chromium.c)

  runhooks_env = bot_config.get('runhooks_env', {})
  yield api.chromium.runhooks(env=runhooks_env)

  # If going to use swarming_client (pinned in src/DEPS), ensure it is
  # compatible with what recipes expect.
  if swarming_tests:
    yield api.swarming.check_client_version()

  tests = []
  # TODO(phajdan.jr): Re-enable checkdeps on Windows when it works with git.
  if not api.platform.is_win:
    tests.append(CheckdepsTest())
  if api.platform.is_linux:
    tests.extend([
        CheckpermsTest(),
        ChecklicensesTest(),
    ])
  tests.append(Deps2GitTest())
  tests.extend(gtest_tests)
  tests.extend(swarming_tests)
  tests.append(NaclIntegrationTest())

  compile_targets.extend(bot_config.get('compile_targets', []))
  compile_targets.extend(api.itertools.chain(
      *[t.compile_targets() for t in tests]))
  # TODO(phajdan.jr): Also compile 'all' on win, http://crbug.com/368831 .
  # Disabled for now because it takes too long and/or fails on Windows.
  if not api.platform.is_win and not bot_config.get('exclude_compile_all'):
    compile_targets = ['all'] + compile_targets
  yield api.chromium.compile(compile_targets,
                             name='compile (with patch)')

  # Do not run tests if the build is already in a failed state.
  if api.step_history.failed:
    return

  # Collect *.isolated hashes for all isolated targets, used when triggering
  # tests on swarming.
  if bot_config.get('use_isolate') or swarming_tests:
    yield api.isolate.find_isolated_tests(api.chromium.output_dir)

  if bot_config['compile_only']:
    return

  if bot_config['chromium_config'] not in ['chromium_chromeos',
                                           'chromium_chromeos_clang']:
    # TODO(phajdan.jr): Make it possible to retry telemetry tests (add JSON).
    # TODO(vadimsh): Trigger swarming tests before telemetry tests.
    yield (
      api.chromium.run_telemetry_unittests(),
      api.chromium.run_telemetry_perf_unittests(),
    )

  def deapply_patch_fn(failing_tests):
    if api.platform.is_win:
      yield api.chromium.taskkill()
    bot_update_json = api.step_history['bot_update'].json.output
    api.gclient.c.solutions[0].revision = str(
        bot_update_json['properties']['got_revision'])
    yield api.bot_update.ensure_checkout(force=True,
                                         patch=False,
                                         always_run=True,
                                         update_presentation=False)
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
      # Search for *.isolated only if enabled in bot config or if some swarming
      # test is being recompiled.
      failing_swarming_tests = set(failing_tests) & set(swarming_tests)
      if bot_config.get('use_isolate') or failing_swarming_tests:
        yield api.isolate.find_isolated_tests(api.chromium.output_dir,
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
    props(buildername='win_chromium_rel') +
    api.platform.name('win') +
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
    props(buildername='linux_chromium_rel') +
    api.platform.name('linux') +
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

  for step in ('bot_update', 'gclient runhooks'):
    yield (
      api.test(step.replace(' ', '_') + '_failure') +
      props(buildername='win_no_bot_update') +
      api.platform.name('win') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('compile_failure') +
    props(buildername='win_chromium_rel') +
    api.platform.name('win') +
    api.step_data('compile (with patch)', retcode=1)
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
    props(buildername='linux_no_bot_update') +
    api.platform.name('linux') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('arm') +
    api.properties.generic(mastername='tryserver.chromium',
                           buildername='linux_arm_cross_compile') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
        'compile_targets': ['browser_tests_run'],
        'gtest_tests': [
          {
            'test': 'browser_tests',
            'args': '--gtest-filter: *NaCl*',
          }, {
            'test': 'base_tests',
            'args': ['--gtest-filter: *NaCl*'],
          },
        ],
      })
    )
  )

  yield (
    api.test('checkperms_failure') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'checkperms (with patch)',
        api.json.output([
            {
                'error': 'Must not have executable bit set',
                'rel_path': 'base/basictypes.h',
            },
        ]))
  )

  yield (
    api.test('checklicenses_failure') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'checklicenses (with patch)',
        api.json.output([
            {
                'filename': 'base/basictypes.h',
                'license': 'UNKNOWN',
            },
        ]))
  )

  # Successfully compiling, isolating and running two targets on swarming.
  yield (
    api.test('swarming_basic') +
    props(buildername='linux_chromium_rel_swarming') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
            'swarming': {
              'can_use_on_swarming_builders': True,
              'shards': 5,
              'platforms': ['linux'],
            },
          },
        ],
      })
    ) +
    api.override_step_data(
        'find isolated tests',
        api.isolate.output_json(['base_unittests', 'browser_tests']))
  )

  # One target (browser_tests) failed to produce *.isolated file.
  yield (
    api.test('swarming_missing_isolated') +
    props(buildername='linux_chromium_rel_swarming') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
        ],
      })
    ) +
    api.override_step_data(
        'find isolated tests',
        api.isolate.output_json(['base_unittests']))
  )

  # One test (base_unittest) failed on swarming. It is retried with
  # deapplied patch.
  yield (
    api.test('swarming_deapply_patch') +
    props(buildername='linux_chromium_rel_swarming') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
        ],
      })
    ) +
    api.override_step_data(
        'find isolated tests',
        api.isolate.output_json(['base_unittests', 'browser_tests'])) +
    api.override_step_data('[swarming] base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data(
        'find isolated tests (2)',
        api.isolate.output_json(['base_unittests']))
  )
