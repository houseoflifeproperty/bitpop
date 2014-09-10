# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'bot_update',
  'chromium',
  'filter',
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
  'swarming',
  'test_utils',
  'tryserver',
]


BUILDERS = {
  'tryserver.chromium.linux': {
    'builders': {
      'linux_arm_cross_compile': {
        'GYP_DEFINES': {
          'target_arch': 'arm',
          'arm_float_abi': 'hard',
          'test_isolation_mode': 'archive',
        },
        'chromium_config': 'chromium',
        'runhooks_env': {
          'GYP_CROSSCOMPILE': '1',
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
      'linux_browser_asan': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'exclude_compile_all': True,
        'chromium_config': 'chromium_asan',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
          'test_spec_file': 'chromium_memory_trybot.json',
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
      'linux_chromium_chromeos_ozone_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'GYP_DEFINES': {
          'use_ozone': '1',
        },
        'chromium_config': 'chromium_chromeos',
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_chromium_chromeos_ozone_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_config': 'chromium_chromeos',
        'GYP_DEFINES': {
          'use_ozone': '1',
        },
        'compile_only': False,
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
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
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
    },
  },
  'tryserver.chromium.win': {
    'builders': {
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


def add_swarming_builder(original, swarming, server):
  """Duplicates builder config on |server|, adding 'enable_swarming: True'."""
  assert server in BUILDERS
  assert original in BUILDERS[server]['builders']
  assert swarming not in BUILDERS[server]['builders']
  conf = BUILDERS[server]['builders'][original].copy()
  conf['enable_swarming'] = True
  BUILDERS[server]['builders'][swarming] = conf


def should_filter_builder(name, regexs, root):
  """Returns true if the builder |name| should be filtered. |regexs| is a list
  of the regular expressions specifying the builders that should *not* be
  filtered. |root| is the root of the project. If |name| completely matches one
  of the regular expressions than false is returned, otherwise true."""
  # Don't run alalyze for other projects, such as blink, as there aren't that
  # many try jobs for them.
  if root != 'src':
    return False
  for regex in regexs:
    match = re.match(regex, name)
    if match and match.end() == len(name):
      return False
  return True


def get_test_names(gtest_tests, swarming_tests):
  """Returns the names of each of the tests in |gtest_tests| and
  |swarming_tests|. These are lists of GTestTest and SwarmingGTestTest."""
  return [test.name for test in gtest_tests + swarming_tests]


def filter_tests(possible_tests, needed_tests):
  """Returns a list of all the tests in |possible_tests| whose name is in
  |needed_tests|."""
  result = []
  for test in possible_tests:
    if test.name in needed_tests:
      result.append(test)
  return result


def get_analyze_config(api, file_name):
  """ Returns the dictionary used to configure certain aspects of the analyze
  step."""
  config_path = api.path.join('testing', 'buildbot', file_name)
  step_result = api.json.read(
    'read analyze test spec',
    api.path['checkout'].join(config_path),
    step_test_data=lambda: api.json.test_api.output({'exclusions': []})
    )
  step_result.presentation.step_text = 'path: %r' % config_path
  return step_result.json.output


add_swarming_builder('linux_chromium_rel', 'linux_chromium_rel_swarming',
                     'tryserver.chromium.linux')
add_swarming_builder('linux_chromium_chromeos_rel',
                     'linux_chromium_chromeos_rel_swarming',
                     'tryserver.chromium.linux')
add_swarming_builder('win_chromium_rel', 'win_chromium_rel_swarming',
                     'tryserver.chromium.win')
add_swarming_builder('win_chromium_x64_rel', 'win_chromium_x64_rel_swarming',
                     'tryserver.chromium.win')
add_swarming_builder('mac_chromium_rel', 'mac_chromium_rel_swarming',
                     'tryserver.chromium.mac')


def build_to_priority(build_properties):
  """Returns the Swarming task priority for the build.

  Does this by determining the build type. Lower is higher priority.
  """
  requester = build_properties.get('requester')
  if requester == 'commit-bot@chromium.org':
    # Commit queue job.
    return 30
  # Normal try job.
  return 50


def GenSteps(api):
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
            api.chromium.steps.SwarmingGTestTest(
                test_name, test_args, swarming_shards))
      else:
        gtest_tests.append(api.chromium.steps.GTestTest(test_name, test_args))

    return compile_targets, gtest_tests, swarming_tests

  def get_bot_config(mastername, buildername):
    master_dict = BUILDERS.get(mastername, {})
    return master_dict.get('builders', {}).get(buildername)

  def compile_and_return_tests(mastername, buildername):
    bot_config = get_bot_config(mastername, buildername)
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

    bot_update_step = api.bot_update.ensure_checkout(force=True)

    test_spec_file = bot_config['testing'].get('test_spec_file',
                                               'chromium_trybot.json')
    test_spec_path = api.path.join('testing', 'buildbot', test_spec_file)
    step_result = api.json.read(
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
            'chromium_configs': [
              'chromium_chromeos',
              'chromium_chromeos_clang'
            ],
            'args': ['--test-launcher-print-test-stdio=always'],
          },
          {
            'test': 'browser_tests',
            'exclude_builders': ['tryserver.chromium.win:win_chromium_x64_rel'],
          },
        ]),
    )
    step_result.presentation.step_text = 'path: %s' % test_spec_path
    test_spec = step_result.json.output

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
        test_spec,
        bot_config.get('enable_swarming'),
        should_use_test)

    runhooks_env = bot_config.get('runhooks_env', {})

    # See if the patch needs to compile on the current platform.
    if isinstance(test_spec, dict) and should_filter_builder(
        buildername, test_spec.get('non_filter_builders', []),
        api.properties.get('root')):
      analyze_config = get_analyze_config(
          api, bot_config['testing'].get('analyze_config_file',
                                         'trybot_analyze_config.json'))
      api.filter.does_patch_require_compile(
          exclusions=analyze_config.get('exclusions', []),
          exes=get_test_names(gtest_tests, swarming_tests),
          env=runhooks_env)
      if not api.filter.result:
        return [], swarming_tests, bot_update_step
      # Patch needs compile. Filter the list of test targets.
      if buildername in test_spec.get('filter_tests_builders', []):
        gtest_tests = filter_tests(gtest_tests, api.filter.matching_exes)
        swarming_tests = filter_tests(swarming_tests, api.filter.matching_exes)

    # Swarming uses Isolate to transfer files to swarming bots.
    # set_isolate_environment modifies GYP_DEFINES to enable test isolation.
    if bot_config.get('use_isolate') or swarming_tests:
      api.isolate.set_isolate_environment(api.chromium.c)

    # If going to use swarming_client (pinned in src/DEPS), ensure it is
    # compatible with what recipes expect.
    if swarming_tests:
      api.swarming.check_client_version()
      # Decide the task priority.
      api.swarming.task_priority = build_to_priority(api.properties)

    api.chromium.runhooks(env=runhooks_env)

    tests = []
    # TODO(phajdan.jr): Re-enable checkdeps on Windows when it works with git.
    if not api.platform.is_win:
      tests.append(api.chromium.steps.CheckdepsTest())
    if api.platform.is_linux:
      tests.extend([
          api.chromium.steps.CheckpermsTest(),
          api.chromium.steps.ChecklicensesTest(),
      ])
    tests.append(api.chromium.steps.Deps2GitTest())

    if (bot_config['chromium_config'] not in ['chromium_chromeos',
                                             'chromium_chromeos_clang']
        and not buildername.startswith('win8')):
      tests.append(api.chromium.steps.TelemetryUnitTests())
      tests.append(api.chromium.steps.TelemetryPerfUnitTests())

    tests.extend(gtest_tests)
    tests.extend(swarming_tests)
    tests.append(api.chromium.steps.NaclIntegrationTest())
    tests.append(api.chromium.steps.MojoPythonTests())

    # test_installer only works on 32-bit builds; http://crbug.com/399643
    # Disabled due to retry issues (http://crbug.com/402081.
    #if api.platform.is_win and api.chromium.c.TARGET_BITS == 32:
    #  tests.append(api.chromium.steps.MiniInstallerTest())

    compile_targets.extend(bot_config.get('compile_targets', []))
    compile_targets.extend(api.itertools.chain(
        *[t.compile_targets(api) for t in tests]))
    # TODO(phajdan.jr): Also compile 'all' on win, http://crbug.com/368831 .
    # Disabled for now because it takes too long and/or fails on Windows.
    if not api.platform.is_win and not bot_config.get('exclude_compile_all'):
      compile_targets = ['all'] + compile_targets
    api.chromium.compile(compile_targets, name='compile (with patch)')

    # Collect *.isolated hashes for all isolated targets, used when triggering
    # tests on swarming.
    if bot_config.get('use_isolate') or swarming_tests:
      api.isolate.find_isolated_tests(api.chromium.output_dir)

    if bot_config['compile_only']:
      tests = []
      swarming_tests = []

    return tests, swarming_tests, bot_update_step

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  tests, swarming_tests, bot_update_step = compile_and_return_tests(
      mastername, buildername)

  def deapply_patch_fn(failing_tests):
    if api.platform.is_win:
      api.chromium.taskkill()
    bot_update_json = bot_update_step.json.output
    api.gclient.c.revisions['src'] = str(
        bot_update_json['properties']['got_revision'])
    api.bot_update.ensure_checkout(force=True,
                                   patch=False,
                                   update_presentation=False)
    try:
      api.chromium.runhooks()
    finally:
      compile_targets = list(api.itertools.chain(
          *[t.compile_targets(api) for t in failing_tests]))
      if compile_targets:
        try:
          api.chromium.compile(
                  compile_targets, name='compile (without patch)')
        except api.step.StepFailure:
          api.chromium.compile(compile_targets,
                               name='compile (without patch, clobber)',
                               force_clobber=True)
        # Search for *.isolated only if enabled in bot config or if some
        # swarming test is being recompiled.
        bot_config = get_bot_config(mastername, buildername)
        failing_swarming_tests = set(failing_tests) & set(swarming_tests)
        if bot_config.get('use_isolate') or failing_swarming_tests:
          api.isolate.find_isolated_tests(api.chromium.output_dir)

  return api.test_utils.determine_new_failures(api, tests, deapply_patch_fn)


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
  def props(config='Release', mastername='tryserver.chromium.linux',
            buildername='linux_chromium_rel', **kwargs):
    kwargs.setdefault('revision', None)
    return api.properties.tryserver(
      build_config=config,
      mastername=mastername,
      buildername=buildername,
      **kwargs
    )

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
    props(buildername='win_chromium_rel', mastername='tryserver.chromium.win') +
    api.platform.name('win') +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           canned_test(passing=False)) +
    api.step_data('gclient runhooks (2)', retcode=1)
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

  for step in ('bot_update', 'gclient runhooks'):
    yield (
      api.test(step.replace(' ', '_') + '_failure') +
      props(buildername='win_no_bot_update',
            mastername='tryserver.chromium.win') +
      api.platform.name('win') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('compile_failure') +
    props(buildername='win_chromium_rel',
          mastername='tryserver.chromium.win') +
    api.platform.name('win') +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('compile_first_failure_linux') +
    props() +
    api.platform.name('linux') +
    api.step_data('compile (with patch)', retcode=1)
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
    api.properties.generic(mastername='tryserver.chromium.linux',
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
        'non_filter_builders': ['.*'],
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
    api.test('check_swarming_version_failure') +
    props(buildername='linux_chromium_rel_swarming') +
    api.platform.name('linux') +
    api.step_data('swarming.py --version', retcode=1) +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
        ],
        'non_filter_builders': ['linux_chromium_rel_swarming'],
      })
      )
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

  yield (
    api.test('mojo_python_tests_failure') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'mojo_python_tests (with patch)',
        api.json.canned_test_output(False))
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # commit queue job.
  yield (
    api.test('swarming_basic_cq') +
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
        'non_filter_builders': ['linux_chromium_rel_swarming'],
      })
    ) +
    api.override_step_data(
        'find isolated tests',
        api.isolate.output_json(['base_unittests', 'browser_tests']))
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # manual try job.
  yield (
    api.test('swarming_basic_try_job') +
    props(
        buildername='linux_chromium_rel_swarming',
        requester='joe@chromium.org') +
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
        'non_filter_builders': ['linux_chromium_rel_swarming'],
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
        'non_filter_builders': ['linux_chromium_rel_swarming'],
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
        'non_filter_builders': ['linux_chromium_rel_swarming'],
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

  # Tests analyze module by not specifying a non_filter_builders.
  yield (
    api.test('no_compile_because_of_analyze') +
    props(buildername='linux_chromium_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    )
  )

  # Verifies analyze skips projects other than src.
  yield (
    api.test('dont_analyze_for_non_src_project') +
    props(buildername='linux_chromium_rel') +
    props(root='blink') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    )
  )

  # Tests analyze module by way of not specifying non_filter_builders and file
  # matching exclusion list. This should result in a compile.
  yield (
    api.test('compile_because_of_analyze_matching_exclusion') +
    props(buildername='linux_chromium_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({})) +
    api.override_step_data('read analyze test spec', api.json.output({
        'exclusions': ['f.*'],
      })
    )
  )

  # Tests analyze module by way of not specifying non_filter_builders and
  # analyze result returning true. This should result in a compile.
  yield (
    api.test('compile_because_of_analyze') +
    props(buildername='linux_chromium_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency', 'targets': []}))
  )

  # Tests analyze module by way of not specifying non_filter_builders and
  # analyze result returning true along with a smaller set of tests.
  yield (
    api.test('compile_because_of_analyze_with_filtered_tests_no_builder') +
    props(buildername='linux_chromium_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
          },
          {
            'test': 'unittests',
          },
        ],
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['browser_tests', 'base_unittests']}))
  )

  # Tests analyze module by way of not specifying non_filter_builders and
  # analyze result returning true along with a smaller set of tests. This
  # specifices a 'filter_test_builder', so that this bot uses the filtered set.
  yield (
    api.test('compile_because_of_analyze_with_filtered_tests') +
    props(buildername='linux_chromium_rel') +
    api.platform.name('linux') +
    api.override_step_data('read test spec', api.json.output({
        'filter_tests_builders': 'linux_chromium_rel',
        'gtest_tests': [
          {
            'test': 'base_unittests',
            'swarming': {'can_use_on_swarming_builders': True},
          },
          {
            'test': 'browser_tests',
          },
          {
            'test': 'unittests',
          },
        ],
      })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['browser_tests', 'base_unittests']}))
  )
