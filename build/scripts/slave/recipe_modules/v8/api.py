# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import math
import collections

from slave import recipe_api
from slave.recipe_modules.v8 import builders


# With more than 23 letters, labels are to big for buildbot's popup boxes.
MAX_LABEL_SIZE = 23

# Make sure that a step is not flooded with log lines.
MAX_FAILURE_LOGS = 10

TEST_CONFIGS = {
  'benchmarks': {
    'name': 'Benchmarks',
    'tests': 'benchmarks',
  },
  'mjsunit': {
    'name': 'Mjsunit',
    'tests': 'mjsunit',
    'add_flaky_step': True,
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': 'mozilla',
    'gclient_apply_config': ['mozilla_tests'],
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': 'cctest mjsunit webkit',
    'add_flaky_step': True,
    'test_args': ['--no-variants', '--shell_flags="--optimize-for-size"'],
  },
  'test262': {
    'name': 'Test262 - no variants',
    'tests': 'test262',
    'test_args': ['--no-variants'],
  },
  'test262_variants': {
    'name': 'Test262',
    'tests': 'test262',
  },
  'v8testing': {
    'name': 'Check',
    'tests': ('mjsunit fuzz-natives cctest message preparser base-unittests '
              'compiler-unittests'),
    'add_flaky_step': True,
  },
  'webkit': {
    'name': 'Webkit',
    'tests': 'webkit',
    'add_flaky_step': True,
  },
}


# TODO(machenbach): Clean up api indirection. "Run" needs the v8 api while
# "gclient_apply_config" needs the general injection module.
class V8Test(object):
  def __init__(self, name):
    self.name = name

  def run(self, api, **kwargs):
    return api.runtest(TEST_CONFIGS[self.name], **kwargs)

  def gclient_apply_config(self, api):
    for c in TEST_CONFIGS[self.name].get('gclient_apply_config', []):
      api.gclient.apply_config(c)


class V8Presubmit(object):
  @staticmethod
  def run(api, **kwargs):
    return api.presubmit()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8CheckInitializers(object):
  @staticmethod
  def run(api, **kwargs):
    return api.check_initializers()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8Fuzzer(object):
  @staticmethod
  def run(api, **kwargs):
    return api.fuzz()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8DeoptFuzzer(object):
  @staticmethod
  def run(api, **kwargs):
    return api.deopt_fuzz()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8GCMole(object):
  @staticmethod
  def run(api, **kwargs):
    return api.gc_mole()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8SimpleLeakCheck(object):
  @staticmethod
  def run(api, **kwargs):
    return api.simple_leak_check()

  @staticmethod
  def gclient_apply_config(_):
    pass


V8_NON_STANDARD_TESTS = {
  'deopt': V8DeoptFuzzer,
  'fuzz': V8Fuzzer,
  'gcmole': V8GCMole,
  'presubmit': V8Presubmit,
  'simpleleak': V8SimpleLeakCheck,
  'v8initializers': V8CheckInitializers,
}


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


class V8Api(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS

  # Map of GS archive names to urls.
  GS_ARCHIVES = {
    'arm_rel_archive': 'gs://chromium-v8/v8-arm-rel',
    'arm_dbg_archive': 'gs://chromium-v8/v8-arm-dbg',
    'linux_rel_archive': 'gs://chromium-v8/v8-linux-rel',
    'linux_dbg_archive': 'gs://chromium-v8/v8-linux-dbg',
    'linux_nosnap_rel_archive': 'gs://chromium-v8/v8-linux-nosnap-rel',
    'linux_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-nosnap-dbg',
    'linux64_rel_archive': 'gs://chromium-v8/v8-linux64-rel',
    'linux64_dbg_archive': 'gs://chromium-v8/v8-linux64-dbg',
    'win32_rel_archive': 'gs://chromium-v8/v8-win32-rel',
    'win32_dbg_archive': 'gs://chromium-v8/v8-win32-dbg',
  }

  def apply_bot_config(self, builders):
    """Entry method for using the v8 api.

    Requires the presence of a bot_config dict for any master/builder pair.
    This bot_config will be used to refine other api methods.
    """

    self.m.step.auto_resolve_conflicts = True
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = builders.get(mastername, {})
    self.bot_config = master_dict.get('builders', {}).get(buildername)
    assert self.bot_config, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))

    self.set_config('v8',
                    optional=True,
                    **self.bot_config.get('v8_config_kwargs', {}))
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('v8_apply_config', []):
      self.apply_config(c)
    if self.c.nacl.update_nacl_sdk:
      self.c.nacl.NACL_SDK_ROOT = str(self.m.path['slave_build'].join(
          'nacl_sdk', 'pepper_current'))
    # Test-specific configurations.
    for t in self.bot_config.get('tests', []):
      self.create_test(t).gclient_apply_config(self.m)
    # Initialize perf_dashboard api if any perf test should run.
    self.m.perf_dashboard.set_default_config()

  def set_bot_config(self, bot_config):
    """Set bot configuration for testing only."""
    self.bot_config = bot_config

  def init_tryserver(self):
    self.m.chromium.apply_config('trybot_flavor')
    self.m.chromium.apply_config('optimized_debug')
    self.apply_config('trybot_flavor')

  def _gclient_checkout(self, may_nuke=False, revert=False):
    if may_nuke:
      try:
        update_step = self.m.gclient.checkout(revert=revert)
      except self.m.step.StepFailure as f:
        # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
        self.m.path.rmcontents('slave build directory',
                               self.m.path['slave_build']),
        update_step = self.m.gclient.checkout()
    else:
      update_step = self.m.gclient.checkout()
    return update_step

  def checkout(self, may_nuke=False, revert=False):
    # Set revision for bot_update including branch information. Needs to be
    # reset afterwards as gclient doesn't understand this info.
    self.m.gclient.c.solutions[0].revision = ('bleeding_edge:%s' %
        self.m.properties.get('revision', 'HEAD'))
    update_step = self.m.bot_update.ensure_checkout(no_shallow=True)

    if not update_step.json.output['did_run']:
      self.m.gclient.c.solutions[0].revision = None
      update_step = self._gclient_checkout(may_nuke=may_nuke, revert=revert)

    # Whatever step is run right before this line needs to emit got_revision.
    self.revision = update_step.presentation.properties['got_revision']

  def runhooks(self, **kwargs):
    env = {}
    if self.c.gyp_env.CC:
      env['CC'] = self.c.gyp_env.CC
    if self.c.gyp_env.CXX:
      env['CXX'] = self.c.gyp_env.CXX
    if self.c.gyp_env.CXX_host:
      env['CXX_host'] = self.c.gyp_env.CXX_host
    if self.c.gyp_env.LINK:
      env['LINK'] = self.c.gyp_env.LINK
    # TODO(machenbach): Make this the default on windows.
    if self.c.gyp_env.GYP_MSVS_VERSION:
      env['GYP_MSVS_VERSION'] = self.c.gyp_env.GYP_MSVS_VERSION
    self.m.chromium.runhooks(env=env, **kwargs)

  @property
  def needs_clang(self):
    return 'clang' in self.bot_config.get('gclient_apply_config', [])

  def update_clang(self):
    # TODO(machenbach): Implement this for windows or unify with chromium's
    # update clang step as soon as it exists.
    self.m.step(
        'update clang',
        [self.m.path['checkout'].join('tools', 'clang',
                                      'scripts', 'update.sh')],
        env={'LLVM_URL': ChromiumSvnSubURL(self.m.gclient.c,
                                           'llvm-project')})

    # TODO(machenbach): Move this path tweaking to the v8 gyp file.
    clang_dir = self.m.path['checkout'].join(
        'third_party', 'llvm-build', 'Release+Asserts', 'bin')
    self.c.gyp_env.CC = self.m.path.join(clang_dir, 'clang')
    self.c.gyp_env.CXX = self.m.path.join(clang_dir, 'clang++')
    self.c.gyp_env.CXX_host = self.m.path.join(clang_dir, 'clang++')
    self.c.gyp_env.LINK = self.m.path.join(clang_dir, 'clang++')

  def update_nacl_sdk(self):
    return self.m.python(
      'update NaCl SDK',
      self.m.path['build'].join('scripts', 'slave', 'update_nacl_sdk.py'),
      ['--pepper-channel', self.c.nacl.update_nacl_sdk],
      cwd=self.m.path['slave_build'],
    )

  def tryserver_lkgr_fallback(self):
    self.m.gclient.apply_config('v8_lkgr')
    self.checkout(True, True)
    self.m.tryserver.maybe_apply_issue()
    self.runhooks()

  @property
  def bot_type(self):
    return self.bot_config.get('bot_type', 'builder_tester')

  @property
  def should_build(self):
    return self.bot_type in ['builder', 'builder_tester']

  @property
  def should_test(self):
    return self.bot_type in ['tester', 'builder_tester']

  @property
  def should_upload_build(self):
    return self.bot_type == 'builder'

  @property
  def should_download_build(self):
    return self.bot_type == 'tester'

  @property
  def perf_tests(self):
    return self.bot_config.get('perf', [])

  def compile(self, **kwargs):
    env={}
    if self.c.nacl.NACL_SDK_ROOT:
      env['NACL_SDK_ROOT'] = self.c.nacl.NACL_SDK_ROOT
    args = []
    if self.c.nacl.compile_extra_args:
      args.extend(self.c.nacl.compile_extra_args)
    self.m.chromium.compile(args, env=env, **kwargs)

  def tryserver_compile(self, fallback_fn, **kwargs):
    try:
      self.compile(name='compile (with patch)')
    except self.m.step.StepFailure as f:
      fallback_fn()
      self.compile(name='compile (with patch, lkgr, clobber)',
                         force_clobber=True)

  def upload_build(self):
    self.m.archive.zip_and_upload_build(
          'package build',
          self.m.chromium.c.build_config_fs,
          self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
          src_dir='v8')

  def download_build(self):
    self.m.path.rmtree(
          'build directory',
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs))

    self.m.archive.download_and_unzip_build(
          'extract build',
          self.m.chromium.c.build_config_fs,
          self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
          src_dir='v8')


  # TODO(machenbach): Pass api already in constructor to avoid redundant api
  # parameter passing later.
  def create_test(self, test):
    """Wrapper that allows to shortcut common tests with their names.
    Returns a runnable test instance.
    """
    if test in V8_NON_STANDARD_TESTS:
      return V8_NON_STANDARD_TESTS[test]()
    else:
      return V8Test(test)

  #TODO(martiniss) convert loop
  def runtests(self):
    with self.m.step.defer_results():
      for t in self.bot_config.get('tests', []):
        self.create_test(t).run(self)

  def presubmit(self):
    self.m.python(
      'Presubmit',
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      ['--testname', 'presubmit'],
      cwd=self.m.path['checkout'],
    )

  def check_initializers(self):
    self.m.step(
      'Static-Initializers',
      ['bash',
       self.m.path['checkout'].join('tools', 'check-static-initializers.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def fuzz(self):
    assert self.m.chromium.c.HOST_PLATFORM == 'linux'
    self.m.step(
      'Fuzz',
      ['bash',
       self.m.path['checkout'].join('tools', 'fuzz-harness.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def gc_mole(self):
    # TODO(machenbach): Make gcmole work with absolute paths. Currently, a
    # particular clang version is installed on one slave in '/b'.
    env = {
      'CLANG_BIN': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole', 'bin')
      ),
      'CLANG_PLUGINS': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole')
      ),
    }
    self.m.step(
      'GCMole',
      ['lua', self.m.path.join('tools', 'gcmole', 'gcmole.lua')],
      cwd=self.m.path['checkout'],
      env=env,
    )

  @recipe_api.composite_step
  def simple_leak_check(self):
    # TODO(machenbach): Add task kill step for windows.
    relative_d8_path = self.m.path.join(
        self.m.path.basename(self.m.chromium.c.build_dir),
        self.m.chromium.c.build_config_fs,
        'd8')
    step_result = self.m.step(
      'Simple Leak Check',
      ['valgrind', '--leak-check=full', '--show-reachable=yes',
       '--num-callers=20', relative_d8_path, '-e', '"print(1+2)"'],
      cwd=self.m.path['checkout'],
    )
    if not 'no leaks are possible' in (step_result.stdout or ''):
      step_result.presentation.status = self.m.step.FAILURE
      raise self.m.step.StepFailure('Failed leak check')

  def deopt_fuzz(self):
    full_args = [
      '--mode', self.m.chromium.c.build_config_fs,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--progress', 'verbose',
      '--buildbot',
    ]

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    self.m.python(
      'Deopt Fuzz',
      self.m.path['checkout'].join('tools', 'run-deopt-fuzzer.py'),
      full_args,
      cwd=self.m.path['checkout'],
    )

  def _command_results_text(self, results, flaky):
    """Returns log lines for all results of a unique command."""
    assert results
    lines = []

    # Add common description for multiple runs.
    flaky_suffix = ' (flaky)' if flaky else ''
    lines.append('Test: %s%s' % (results[0]['name'], flaky_suffix))
    lines.append('Flags: %s' % " ".join(results[0]['flags']))
    lines.append('Command: %s' % results[0]['command'])
    lines.append('')

    # Add results for each run of a command.
    for result in sorted(results, key=lambda r: int(r['run'])):
      lines.append('Run #%d' % int(result['run']))
      lines.append('Exit code: %s' % result['exit_code'])
      lines.append('Result: %s' % result['result'])
      lines.append('')
      if result['stdout']:
        lines.append('Stdout:')
        lines.extend(result['stdout'].splitlines())
        lines.append('')
      if result['stderr']:
        lines.append('Stderr:')
        lines.extend(result['stderr'].splitlines())
        lines.append('')
    return lines

  def _update_test_presentation(self, results, presentation):
    def all_same(items):
      return all(x == items[0] for x in items)

    if not results:
      return

    unique_results = {}
    for result in results:
      # Use test base name as UI label (without suite and directory names).
      label = result['name'].split('/')[-1]
      # Truncate the label if it is still too long.
      if len(label) > MAX_LABEL_SIZE:
        label = label[:MAX_LABEL_SIZE - 2] + '..'
      # Group tests with the same label (usually the same test that ran under
      # different configurations).
      unique_results.setdefault(label, []).append(result)

    failure_count = 0
    flake_count = 0
    for label in sorted(unique_results.keys()[:MAX_FAILURE_LOGS]):
      lines = []

      # Group results by command. The same command might have run multiple
      # times to detect flakes.
      results_per_command = {}
      for result in unique_results[label]:
        results_per_command.setdefault(result['command'], []).append(result)

      for command in results_per_command:
        # Determine flakiness. A test is flaky if not all results from a unique
        # command are the same (e.g. all 'FAIL').
        flaky = not all_same(map(lambda x: x['result'],
                                 results_per_command[command]))

        # Count flakes and failures for summary. The v8 test driver reports
        # failures and reruns of failures.
        flake_count += int(flaky)
        failure_count += int(not flaky)

        lines += self._command_results_text(results_per_command[command],
                                            flaky)
      presentation.logs[label] = lines

    # Summary about flakes and failures.
    presentation.step_text += ('failures: %d<br/>flakes: %d<br/>' %
                               (failure_count, flake_count))

  @recipe_api.composite_step
  def _runtest(self, name, test, flaky_tests=None, **kwargs):
    env = {}
    target = self.m.chromium.c.build_config_fs
    if self.c.nacl.update_nacl_sdk:
      # TODO(machenbach): NaCl circumvents the buildbot naming conventions and
      # uses v8 flavor. Make this more uniform.
      target = target.lower()
    full_args = [
      '--target', target,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--testname', test['tests'],
    ]

    # Add test-specific test arguments.
    full_args += test.get('test_args', [])

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    if self.c.testing.SHARD_COUNT > 1:
      full_args += [
        '--shard_count=%d' % self.c.testing.SHARD_COUNT,
        '--shard_run=%d' % self.c.testing.SHARD_RUN,
      ]

    if flaky_tests:
      full_args += ['--flaky-tests', flaky_tests]

    # Arguments and environment for asan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') == 1:
      full_args.append('--asan')
      env['ASAN_SYMBOLIZER_PATH'] = self.m.path['checkout'].join(
          'third_party', 'llvm-build', 'Release+Asserts', 'bin',
          'llvm-symbolizer')

    # Arguments and environment for tsan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('tsan') == 1:
      full_args.append('--tsan')
      env['TSAN_OPTIONS'] = " ".join([
        'external_symbolizer_path=%s' %
            self.m.path['checkout'].join(
                'third_party', 'llvm-build', 'Release+Asserts', 'bin',
                'llvm-symbolizer'),
        'exit_code=0',
        'report_thread_leaks=0',
        'history_size=7',
        'report_destroy_locked=0',
      ])

    # Environment for nacl builds:
    if self.c.nacl.NACL_SDK_ROOT:
      env['NACL_SDK_ROOT'] = self.c.nacl.NACL_SDK_ROOT

    # Default callbacks if the show_test_results feature is turned off.
    step_test_data = None

    if self.c.testing.show_test_results:
      full_args += ['--json-test-results',
                    self.m.json.output(add_json_log=False)]
      def step_test_data():
        return self.test_api.output_json(
            self._test_data.get('test_failures', False),
            self._test_data.get('wrong_results', False))

    try:
      self.m.python(
        name,
        self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
        full_args,
        cwd=self.m.path['checkout'],
        env=env,
        step_test_data=step_test_data,
        **kwargs
      )
    finally:
      # Show test results independent of the step result.
      step_result = self.m.step.active_result
      if self.c.testing.show_test_results:
        r = step_result.json.output
        # The output is expected to be a list of architecture dicts that
        # each contain a results list. On buildbot, there is only one
        # architecture.
        if (r and isinstance(r, list) and isinstance(r[0], dict)):
          self._update_test_presentation(r[0]['results'],
                                         step_result.presentation)

        # Check integrity of the last output. The json list is expected to
        # contain only one element for one (architecture, build config type)
        # pair on the buildbot.
        result = step_result.json.output
        if result and len(result) > 1:
          self.m.python.inline(
              name,
              r"""
              import sys
              print 'Unexpected results set present.'
              sys.exit(1)
              """)

  def runtest(self, test, **kwargs):
    # Get the flaky-step configuration default per test.
    add_flaky_step = test.get('add_flaky_step', False)

    # Overwrite the flaky-step configuration on a per builder basis as some
    # types of builders (e.g. branch, try) don't have any flaky steps.
    if self.c.testing.add_flaky_step is not None:
      add_flaky_step = self.c.testing.add_flaky_step
    if add_flaky_step:
      try:
        self._runtest(test['name'], test, flaky_tests='skip', **kwargs)
      finally:
        self._runtest(test['name'] + ' - flaky', test, flaky_tests='run',
                      **kwargs)
    else:
      self._runtest(test['name'], test, **kwargs)

  def runperf(self, tests, perf_configs, category=None):
    """Run v8 performance tests and upload results.

    Args:
      tests: A list of tests from perf_configs to run.
      perf_configs: A mapping from test name to a suite configuration json.
      category: Optionally use bot nesting level as category. Bot names are
                irrelevant if several different bots run in the same category
                like ia32.
    """

    results_mapping = collections.defaultdict(dict)
    def run_single_perf_test(test, name, json_file):
      """Call the v8 benchmark suite runner.

      Performance results are saved in the json test results file as a dict with
      'errors' for accumulated errors and 'traces' for the measurements.
      """
      full_args = [
        '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
        '--buildbot',
        '--json-test-results', self.m.json.output(add_json_log=False),
        json_file,
      ]

      step_test_data = lambda: self.test_api.perf_json(
          self._test_data.get('perf_failures', False))

      try:
        self.m.python(
          name,
          self.m.path['checkout'].join('tools', 'run_benchmarks.py'),
          full_args,
          cwd=self.m.path['checkout'],
          step_test_data=step_test_data,
        )
      finally:
        results_mapping[t][name] = step_result = self.m.step.active_result
        errors = step_result.json.output['errors']
        if errors:
          step_result.presentation.logs['Errors'] = errors
        else:
          # Add a link to the dashboard. This assumes the naming convention
          # step name == suite name. If this convention didn't hold, we'd need
          # to use the path from the json output graphs here.
          self.m.perf_dashboard.add_dashboard_link(
              step_result.presentation,
              'v8/%s' % name,
              self.revision,
              bot=category)

    def mean(values):
      return float(sum(values)) / len(values)

    def variance(values, average):
      return map(lambda x: (x - average) ** 2, values)

    def standard_deviation(values, average):
      return math.sqrt(mean(variance(values, average)))

    failed = False
    for t in tests:
      assert perf_configs[t]
      assert perf_configs[t]['name']
      assert perf_configs[t]['json']
      try:
        run_single_perf_test(
            t, perf_configs[t]['name'], perf_configs[t]['json'])
      except self.m.step.StepFailure:
        failed = True

    # Make sure that bots that run perf tests have a revision property.
    if tests:
      assert self.revision, ('Revision must be specified for perf tests as '
                             'they upload data to the perf dashboard.')

    # Collect all perf data of the previous steps.
    points = []
    for t in tests:
      step = results_mapping[t][perf_configs[t]['name']]
      for trace in step.json.output['traces']:
        # Make 'v8' the root of all standalone v8 performance tests.
        test_path = '/'.join(['v8'] + trace['graphs'])

        # Ignore empty traces.
        # TODO(machenbach): Show some kind of failure on the waterfall on empty
        # traces without skipping to upload.
        if not trace['results']:
          continue

        values = map(float, trace['results'])
        average = mean(values)

        p = self.m.perf_dashboard.get_skeleton_point(
            test_path, self.revision, str(average))
        p['units'] = trace['units']
        p['bot'] = category or p['bot']
        p['supplemental_columns'] = {'a_default_rev': 'r_v8_rev',
                                     'r_v8_rev': self.revision}

        # A trace might provide a value for standard deviation if the test
        # driver already calculated it, otherwise calculate it here.
        p['error'] = (trace.get('stddev') or
                      str(standard_deviation(values, average)))

        points.append(p)

    # Send all perf data to the perf dashboard in one step.
    if points:
      self.m.perf_dashboard.post(points)

    if failed:
      raise self.m.step.StepFailure('One or more performance tests failed.')
