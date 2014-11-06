# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class Test(object):
  """
  Base class for tests that can be retried after deapplying a previously
  applied patch.
  """

  def __init__(self):
    super(Test, self).__init__()
    self._test_runs = {}

  @property
  def abort_on_failure(self):
    """If True, abort build when test fails."""
    return False

  @property
  def name(self):  # pragma: no cover
    """Name of the test."""
    raise NotImplementedError()

  def pre_run(self, api, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    return []

  def run(self, api, suffix):  # pragma: no cover
    """Run the test. suffix is 'with patch' or 'without patch'."""
    raise NotImplementedError()

  def post_run(self, api, suffix):  # pragma: no cover
    """Steps to execute after running the test."""
    return []

  def has_valid_results(self, api, suffix):  # pragma: no cover
    """
    Returns True if results (failures) are valid.

    This makes it possible to distinguish between the case of no failures
    and the test failing to even report its results in machine-readable
    format.
    """
    raise NotImplementedError()

  def failures(self, api, suffix):  # pragma: no cover
    """Return list of failures (list of strings)."""
    raise NotImplementedError()

  @property
  def uses_swarming(self):
    """Returns true if the test uses swarming."""
    return False

  def _step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix."""
    if not suffix:
      return self.name
    return '%s (%s)' % (self.name, suffix)


class ArchiveBuildStep(Test):
  def __init__(self, gs_bucket, gs_acl=None):
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl

  def run(self, api, suffix):
    return api.chromium.archive_build(
        'archive build',
        self.gs_bucket,
        gs_acl=self.gs_acl,
    )

  @staticmethod
  def compile_targets(_):
    return []


class CheckdepsTest(Test):  # pylint: disable=W0232
  name = 'checkdeps'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.checkdeps(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    results = self._test_runs[suffix].json.output
    result_set = set()
    for result in results:
      for violation in result['violations']:
        result_set.add((result['dependee_path'], violation['include_path']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]


class CheckpermsTest(Test):  # pylint: disable=W0232
  name = 'checkperms'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.checkperms(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    results = self._test_runs[suffix].json.output
    result_set = set()
    for result in results:
      result_set.add((result['rel_path'], result['error']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]

class ChecklicensesTest(Test):  # pylint: disable=W0232
  name = 'checklicenses'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.checklicenses(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    results = self._test_runs[suffix].json.output
    result_set = set()
    for result in results:
      result_set.add((result['filename'], result['license']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]


class Deps2GitTest(Test):  # pylint: disable=W0232
  name = 'deps2git'

  def __init__(self):
    super(Deps2GitTest, self).__init__()

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    try:
      api.chromium.deps2git(suffix)
    finally:
      self._test_runs[suffix] = api.step.active_result

    api.chromium.deps2submodules()

    return self._test_runs[suffix]

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.output


class LocalGTestTest(Test):
  def __init__(self, name, args=None, compile_targets=None,
               flakiness_dash=False):
    super(LocalGTestTest, self).__init__()
    self._name = name
    self._args = args or []
    self.flakiness_dash = flakiness_dash

  @property
  def name(self):
    return self._name

  def compile_targets(self, api):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return [self.name + '_apk']

    # On iOS we rely on 'All' target being compiled instead of using
    # individual targets.
    if api.chromium.c.TARGET_PLATFORM == 'ios':
      return []

    return [self.name]

  def run(self, api, suffix):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return api.chromium_android.run_test_suite(
          self.name, self._args)

    # Copy the list because run can be invoked multiple times and we modify
    # the local copy.
    args = self._args[:]

    if suffix == 'without patch':
      args.append(api.chromium.test_launcher_filter(
                      self.failures(api, 'with patch')))

    kwargs = {}

    try:
      api.chromium.runtest(
          self.name, args,
          annotate='gtest',
          xvfb=True,
          name=self._step_name(suffix),
          test_type=self.name,
          flakiness_dash=self.flakiness_dash,
          step_test_data=lambda: api.json.test_api.canned_gtest_output(True),
          test_launcher_summary_output=api.json.gtest_results(add_json_log=False),
          **kwargs)
    finally:
      step_result = api.step.active_result
      self._test_runs[suffix] = step_result

      r = step_result.json.gtest_results
      p = step_result.presentation

      if r.valid:
        p.step_text += api.test_utils.format_step_text([
            ['failures:', r.failures]
        ])
    return step_result

  def has_valid_results(self, api, suffix):
    gtest_results = self._test_runs[suffix].json.gtest_results
    if not gtest_results.valid:  # pragma: no cover
      return False
    global_tags = gtest_results.raw.get('global_tags', [])
    return 'UNRELIABLE_RESULTS' not in global_tags

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.gtest_results.failures


def generate_gtest(api, mastername, buildername, test_spec,
                   enable_swarming=False):
  def canonicalize_test(test):
    if isinstance(test, basestring):
      canonical_test = {'test': test}
    else:
      canonical_test = test.copy()

    canonical_test.setdefault('shard_index', 0)
    canonical_test.setdefault('total_shards', 1)
    return canonical_test

  def get_tests(api):
    return [canonicalize_test(t) for t in
            test_spec.get(buildername, {}).get('gtest_tests', [])]

  for test in get_tests(api):
    args = test.get('args', [])
    if test['shard_index'] != 0 or test['total_shards'] != 1:
      args.extend(['--test-launcher-shard-index=%d' % test['shard_index'],
                   '--test-launcher-total-shards=%d' % test['total_shards']])
    use_swarming = False
    swarming_shards = 1
    if enable_swarming:
      swarming_spec = test.get('swarming', {})
      if swarming_spec.get('can_use_on_swarming_builders'):
        use_swarming = True
        swarming_shards = swarming_spec.get('shards', 1)
    yield GTestTest(str(test['test']), args=args, flakiness_dash=True,
                    enable_swarming=use_swarming,
                    swarming_shards=swarming_shards)


class DynamicPerfTests(Test):
  def __init__(self, browser, perf_id, shard_index, num_shards):
    self.browser = browser
    self.perf_id = perf_id
    self.shard_index = shard_index
    self.num_shards = num_shards

  def run(self, api, suffix):
    exception = None
    tests = api.chromium.list_perf_tests(self.browser, self.num_shards)
    tests = dict((k, v) for k, v in tests.json.output['steps'].iteritems()
        if v['device_affinity'] == self.shard_index)
    for test_name, test in sorted(tests.iteritems()):
      test_name = str(test_name)
      annotate = api.chromium.get_annotate_by_test_name(test_name)
      cmd = test['cmd'].split()
      try:
        api.chromium.runtest(
            cmd[1] if len(cmd) > 1 else cmd[0],
            args=cmd[2:],
            name=test_name,
            annotate=annotate,
            python_mode=True,
            results_url='https://chromeperf.appspot.com',
            perf_dashboard_id=test.get('perf_dashboard_id', test_name),
            perf_id=self.perf_id,
            test_type=test.get('perf_dashboard_id', test_name),
            xvfb=True)
      except api.step.StepFailure as f:
        exception = f
    if exception:
      raise exception

  @staticmethod
  def compile_targets(_):
    return []


class SwarmingGTestTest(Test):
  def __init__(self, name, args=None, shards=1):
    self._name = name
    self._args = args or []
    self._shards = shards
    self._tasks = {}
    self._results = {}

  @property
  def name(self):
    return self._name

  def compile_targets(self, _):
    # <X>_run target depends on <X>, and then isolates it invoking isolate.py.
    # It is a convention, not a hard coded rule.
    return [self._name + '_run']

  def pre_run(self, api, suffix):
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
          args=[self._name])

    # If rerunning without a patch, run only tests that failed.
    args = self._args[:]
    if suffix == 'without patch':
      failed_tests = sorted(self.failures(api, 'with patch'))
      args.append('--gtest_filter=%s' % ':'.join(failed_tests))

    # Trigger the test on swarming.
    self._tasks[suffix] = api.swarming.gtest_task(
        title=self._step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        test_launcher_summary_output=api.json.gtest_results(
            add_json_log=False),
        extra_args=args)
    return api.swarming.trigger([self._tasks[suffix]])

  def run(self, api, suffix):  # pylint: disable=R0201
    """Not used. All logic in pre_run, post_run."""
    return []

  def post_run(self, api, suffix):
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
          args=[self._name])

    # Wait for test on swarming to finish. If swarming infrastructure is
    # having issues, this step produces no valid *.json test summary, and
    # 'has_valid_results' returns False.
    step_results = api.swarming.collect_each([self._tasks[suffix]])

    # TODO(martiniss) make this loop better. It's kinda hacky.
    failed_results = []
    try:
      while True:
        try:
          step_result = next(step_results)
        except api.step.StepFailure as f:
          step_result = api.step.active_result
          failed_results.append(step_result)

        r = step_result.json.gtest_results
        p = step_result.presentation
        t = step_result.swarming_task
        missing_shards = r.raw.get('missing_shards') or []
        for index in missing_shards:
          p.links['missing shard #%d' % index] = t.get_shard_view_url(index)
        if r.valid:
          p.step_text += api.test_utils.format_step_text([
              ['failures:', r.failures]
          ])
        self._results[suffix] = r
    except StopIteration:
      pass
    finally:
      if failed_results:
        raise api.step.StepFailure(
            'Swarming failed due to %d result failures' % len(failed_results))

  def has_valid_results(self, api, suffix):
    # Test wasn't triggered or wasn't collected.
    if suffix not in self._tasks or not suffix in self._results:
      return False
    # Test ran, but failed to produce valid *.json.
    gtest_results = self._results[suffix]
    if not gtest_results.valid:  # pragma: no cover
      return False
    global_tags = gtest_results.raw.get('global_tags', [])
    return 'UNRELIABLE_RESULTS' not in global_tags

  def failures(self, api, suffix):
    assert self.has_valid_results(api, suffix)
    return self._results[suffix].failures

  @property
  def uses_swarming(self):
    return True


class GTestTest(Test):
  def __init__(self, name, args=None, compile_targets=None,
               flakiness_dash=False, enable_swarming=False, swarming_shards=1):
    super(GTestTest, self).__init__()
    self._name = name
    self._args = args
    if enable_swarming:
      self._test = SwarmingGTestTest(name, args, swarming_shards)
    else:
      self._test = LocalGTestTest(name, args, compile_targets, flakiness_dash)

  def force_swarming(self, swarming_shards=1):
    self._test = SwarmingGTestTest(self._name, self._args, swarming_shards)

  @property
  def name(self):
    return self._test.name

  def compile_targets(self, api):
    return self._test.compile_targets(api)

  def pre_run(self, api, suffix):
    return self._test.pre_run(api, suffix)

  def run(self, api, suffix):
    return self._test.run(api, suffix)

  def post_run(self, api, suffix):
    return self._test.post_run(api, suffix)

  def has_valid_results(self, api, suffix):
    return self._test.has_valid_results(api, suffix)

  def failures(self, api, suffix):
    return self._test.failures(api, suffix)

  @property
  def uses_swarming(self):
    return self._test.uses_swarming


class PythonBasedTest(Test):
  @staticmethod
  def compile_targets(_):
    return []

  def run_step(self, api, suffix, cmd_args, **kwargs):
    raise NotImplementedError()

  def run(self, api, suffix):
    cmd_args = ['--write-full-results-to',
                api.json.test_results(add_json_log=False)]
    if suffix == 'without patch':
      cmd_args.extend(self.failures(api, 'with patch'))

    try:
      self.run_step(
          api,
          suffix,
          cmd_args,
          step_test_data=lambda: api.json.test_api.canned_test_output(True))
    finally:
      step_result = api.step.active_result
      r = step_result.json.test_results
      p = step_result.presentation
      p.step_text += api.test_utils.format_step_text([
        ['unexpected_failures:', r.unexpected_failures.keys()],
      ])
      self._test_runs[suffix] = step_result

    return step_result

  def has_valid_results(self, api, suffix):
    # TODO(dpranke): we should just return zero/nonzero for success/fail.
    # crbug.com/357866
    step = self._test_runs[suffix]
    return (step.json.test_results.valid and
            step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS and
            (step.retcode == 0) or self.failures(api, suffix))

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.test_results.unexpected_failures


class MojoPythonTests(PythonBasedTest):  # pylint: disable=W0232
  name = 'mojo_python_tests'

  def run_step(self, api, suffix, cmd_args, **kwargs):
    return api.python(self._step_name(suffix),
                      api.path['checkout'].join('mojo', 'tools',
                                                'run_mojo_python_tests.py'),
                      cmd_args,
                      **kwargs)


class MojoPythonBindingsTests(PythonBasedTest):  # pylint: disable=W0232
  name = 'mojo_python_bindings_tests'

  def run_step(self, api, suffix, cmd_args, **kwargs):
    component = api.chromium.c.gyp_env.GYP_DEFINES.get('component', None)
    # Python modules are not build for the component build.
    if component == 'shared_library':
      return None
    args = cmd_args
    args.extend(['--build-dir', api.chromium.output_dir])
    return api.python(
        self._step_name(suffix),
        api.path['checkout'].join('mojo', 'tools',
                                  'run_mojo_python_bindings_tests.py'),
        args,
        **kwargs)

  @staticmethod
  def compile_targets(api):
    return ['mojo_python', 'mojo_public_test_interfaces']


class PrintPreviewTests(PythonBasedTest):  # pylint: disable=W032
  name = 'print_preview_tests'

  def run_step(self, api, suffix, cmd_args, **kwargs):
    platform_arg = '.'.join(['browser_test',
        api.platform.normalize_platform_name(api.platform.name)])
    args = cmd_args
    path = api.path['checkout'].join(
        'third_party', 'WebKit', 'Tools', 'Scripts', 'run-webkit-tests')
    args.extend(['--platform', platform_arg])

    # This is similar to how api.chromium.run_telemetry_test() sets the
    # environment variable for the sandbox.
    env = {}
    if api.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = api.path.join(
          '/opt', 'chromium', 'chrome_sandbox')

    return api.chromium.runtest(
        test=path,
        args=args,
        xvfb=True,
        name=self._step_name(suffix),
        python_mode=True,
        env=env,
        **kwargs)

  @staticmethod
  def compile_targets(api):
    targets = ['browser_tests', 'blink_tests']
    if api.platform.is_win:
      targets.append('crash_service')

    return targets


class TelemetryUnitTests(PythonBasedTest):  # pylint: disable=W0232
  name = 'telemetry_unittests'

  @staticmethod
  def compile_targets(_):
    return ['chrome']

  def run_step(self, api, suffix, cmd_args, **kwargs):
    return api.chromium.run_telemetry_unittests(suffix, cmd_args, **kwargs)


class TelemetryPerfUnitTests(PythonBasedTest):
  name = 'telemetry_perf_unittests'

  @staticmethod
  def compile_targets(_):
    return ['chrome']

  def run_step(self, api, suffix, cmd_args, **kwargs):
    return api.chromium.run_telemetry_perf_unittests(suffix, cmd_args,
                                                     **kwargs)


class NaclIntegrationTest(Test):  # pylint: disable=W0232
  name = 'nacl_integration'

  @staticmethod
  def compile_targets(_):
    return ['chrome']

  def run(self, api, suffix):
    args = [
        '--mode', api.chromium.c.build_config_fs,
        '--json_build_results_output_file', api.json.output(),
    ]

    try:
      api.python(
        self._step_name(suffix),
        api.path['checkout'].join('chrome',
                          'test',
                          'nacl_test_injection',
                          'buildbot_nacl_integration.py'),
        args,
        step_test_data=lambda: api.m.json.test_api.output([]))
    finally:
      self._test_runs[suffix] = api.step.active_result

  def has_valid_results(self, api, suffix):
    return self._test_runs[suffix].json.output is not None

  def failures(self, api, suffix):
    failures = self._test_runs[suffix].json.output
    return [f['raw_name'] for f in failures]


class AndroidInstrumentationTest(Test):
  def __init__(self, name, compile_target, test_data=None,
               adb_install_apk=None):
    self._name = name
    self.compile_target = compile_target

    self.test_data = test_data
    self.adb_install_apk = adb_install_apk

  @property
  def name(self):
    return self._name

  def run(self, api, suffix):
    assert api.chromium.c.TARGET_PLATFORM == 'android'
    if self.adb_install_apk:
      api.chromium_android.adb_install_apk(
          self.adb_install_apk[0], self.adb_install_apk[1])
    api.chromium_android.run_instrumentation_suite(
        self.name, test_data=self.test_data,
        flakiness_dashboard='test-results.appspot.com',
        verbose=True)

  def compile_targets(self, _):
    return [self.compile_target]


class BlinkTest(Test):
  # TODO(dpranke): This should be converted to a PythonBasedTest, although it
  # will need custom behavior because we archive the results as well.

  name = 'webkit_tests'

  def __init__(self, api):
    super(BlinkTest, self).__init__()
    self.results_dir = api.path['slave_build'].join('layout-test-results')
    self.layout_test_wrapper = api.path['build'].join(
        'scripts', 'slave', 'chromium', 'layout_test_wrapper.py')

  def run(self, api, suffix):
    args = ['--target', api.chromium.c.BUILD_CONFIG,
            '-o', self.results_dir,
            '--build-dir', api.chromium.c.build_dir,
            '--json-test-results', api.json.test_results(add_json_log=False)]
    if suffix == 'without patch':
      test_list = "\n".join(self.failures(api, 'with patch'))
      args.extend(['--test-list', api.raw_io.input(test_list),
                   '--skipped', 'always'])

    if 'oilpan' in api.properties['buildername']:
      args.extend(['--additional-expectations',
                   api.path['checkout'].join('third_party', 'WebKit',
                                             'LayoutTests',
                                             'OilpanExpectations')])

    try:
      step_result = api.chromium.runtest(self.layout_test_wrapper,
                                         args, name=self._step_name(suffix))
    except api.step.StepFailure as f:
      step_result = f.result

    self._test_runs[suffix] = step_result

    if step_result:
      r = step_result.json.test_results
      p = step_result.presentation

      p.step_text += api.test_utils.format_step_text([
        ['unexpected_flakes:', r.unexpected_flakes.keys()],
        ['unexpected_failures:', r.unexpected_failures.keys()],
        ['Total executed: %s' % r.num_passes],
      ])

      if r.unexpected_flakes or r.unexpected_failures:
        p.status = api.step.WARNING
      else:
        p.status = api.step.SUCCESS

    if suffix == 'with patch':
      buildername = api.properties['buildername']
      buildnumber = api.properties['buildnumber']

      archive_layout_test_results = api.path['build'].join(
          'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

      archive_result = api.python(
        'archive_webkit_tests_results',
        archive_layout_test_results,
        [
          '--results-dir', self.results_dir,
          '--build-dir', api.chromium.c.build_dir,
          '--build-number', buildnumber,
          '--builder-name', buildername,
          '--gs-bucket', 'gs://chromium-layout-test-archives',
        ] + api.json.property_args(),
      )

      base = (
        "https://storage.googleapis.com/chromium-layout-test-archives/%s/%s"
        % (buildername, buildnumber))

      archive_result.presentation.links['layout_test_results'] = (
          base + '/layout-test-results/results.html')
      archive_result.presentation.links['(zip)'] = (
          base + '/layout-test-results.zip')

  def has_valid_results(self, api, suffix):
    step = self._test_runs[suffix]
    # TODO(dpranke): crbug.com/357866 - note that all comparing against
    # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
    # or abnormally; it does not tell us how many failures there actually
    # were, which might be much higher (up to 5000 diffs, where we
    # would bail out early with --exit-after-n-failures) or lower
    # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
    # which case the retcode is actually 130
    return (step.json.test_results.valid and
            step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS)

  def failures(self, api, suffix):
    return self._test_runs[suffix].json.test_results.unexpected_failures


class MiniInstallerTest(PythonBasedTest):  # pylint: disable=W0232
  name = 'test_installer'

  @staticmethod
  def compile_targets(_):
    return ['mini_installer']

  def run_step(self, api, suffix, cmd_args, **kwargs):
    test_path = api.path['checkout'].join('chrome', 'test', 'mini_installer')
    args = [
      '--build-dir', api.chromium.c.build_dir,
      '--target', api.chromium.c.build_config_fs,
      '--force-clean',
      '--config', test_path.join('config', 'config.config'),
    ]
    args.extend(cmd_args)
    return api.python(
      self._step_name(suffix),
      test_path.join('test_installer.py'),
      args,
      **kwargs)


class GenerateTelemetryProfileStep(Test):
  name = 'generate_telemetry_profiles'

  def __init__(self, target, profile_type_to_create):
    super(GenerateTelemetryProfileStep, self).__init__()
    self._target = target
    self._profile_type_to_create = profile_type_to_create

  def run(self, api, suffix):
    args = ['--run-python-script',
            '--target', self._target,
            api.path['build'].join('scripts', 'slave',
                                   'generate_profile_shim.py'),
            '--target=' + self._target,
            '--profile-type-to-generate=' + self._profile_type_to_create]
    api.python('generate_telemetry_profiles',
               api.path['build'].join('scripts', 'slave','runtest.py'),
               args)

  @property
  def abort_on_failure(self):
    """If True, abort build when test fails."""
    return True

  @staticmethod
  def compile_targets(_):
    return []

IOS_TESTS = [
  GTestTest('base_unittests'),
  GTestTest('components_unittests'),
  GTestTest('crypto_unittests'),
  GTestTest('gfx_unittests'),
  GTestTest('url_unittests'),
  GTestTest('content_unittests'),
  GTestTest('net_unittests'),
  GTestTest('ui_unittests'),
  GTestTest('ui_ios_unittests'),
  GTestTest('sync_unit_tests'),
  GTestTest('sql_unittests'),
]
