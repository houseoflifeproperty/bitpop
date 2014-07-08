# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave import recipe_util


class TestLauncherFilterFileInputPlaceholder(recipe_util.Placeholder):
  def __init__(self, api, tests):
    self.raw = api.m.raw_io.input('\n'.join(tests))
    super(TestLauncherFilterFileInputPlaceholder, self).__init__()

  def render(self, test):
    result = self.raw.render(test)
    if not test.enabled:  # pragma: no cover
      result[0] = '--test-launcher-filter-file=%s' % result[0]
    return result

  def result(self, presentation, test):
    return self.raw.result(presentation, test)


class ChromiumApi(recipe_api.RecipeApi):
  def get_config_defaults(self):
    return {
      'HOST_PLATFORM': self.m.platform.name,
      'HOST_ARCH': self.m.platform.arch,
      'HOST_BITS': self.m.platform.bits,

      'TARGET_PLATFORM': self.m.platform.name,
      'TARGET_ARCH': self.m.platform.arch,

      # NOTE: This is replicating logic which lives in
      # chrome/trunk/src/build/common.gypi, which is undesirable. The desired
      # end-state is that all the configuration logic lives in one place
      # (in chromium/config.py), and the buildside gypfiles are as dumb as
      # possible. However, since the recipes need to accurately contain
      # {TARGET,HOST}_{BITS,ARCH,PLATFORM}, for use across many tools (of which
      # gyp is one tool), we're taking a small risk and replicating the logic
      # here.
      'TARGET_BITS': (
        32 if self.m.platform.name in ('mac', 'win')
        else self.m.platform.bits),

      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release')
    }

  @property
  def output_dir(self):
    """Return the path to the built executable directory."""
    return self.c.build_dir.join(self.c.build_config_fs)

  def compile(self, targets=None, name=None, abort_on_failure=True,
              force_clobber=False, **kwargs):
    """Return a compile.py invocation."""
    targets = targets or self.c.compile_py.default_targets.as_jsonish()
    assert isinstance(targets, (list, tuple))

    args = [
      '--target', self.c.build_config_fs,
      '--src-dir', self.m.path['checkout'],
    ]
    if self.c.compile_py.build_tool:
      args += ['--build-tool', self.c.compile_py.build_tool]
    if self.c.compile_py.compiler:
      args += ['--compiler', self.c.compile_py.compiler]
    if self.c.compile_py.mode:
      args += ['--mode', self.c.compile_py.mode]
    if self.c.compile_py.goma_dir:
      args += ['--goma-dir', self.c.compile_py.goma_dir]
    if (self.m.properties.get('clobber') is not None or
        self.c.compile_py.clobber or
        force_clobber):
      args.append('--clobber')
    if self.c.compile_py.pass_arch_flag:
      args += ['--arch', self.c.gyp_env.GYP_DEFINES['target_arch']]
    args.append('--')
    args.extend(targets)
    return self.m.python(name or 'compile',
                         self.m.path['build'].join('scripts', 'slave',
                                                   'compile.py'),
                         args, abort_on_failure=abort_on_failure, **kwargs)

  @recipe_util.returns_placeholder
  def test_launcher_filter(self, tests):
    return TestLauncherFilterFileInputPlaceholder(self, tests)

  def runtest(self, test, args=None, xvfb=False, name=None, annotate=None,
              results_url=None, perf_dashboard_id=None, test_type=None,
              generate_json_file=False, results_directory=None,
              python_mode=False, spawn_dbus=True, parallel=False,
              revision=None, webkit_revision=None, master_class_name=None,
              test_launcher_summary_output=None, flakiness_dash=None,
              perf_id=None, **kwargs):
    """Return a runtest.py invocation."""
    args = args or []
    assert isinstance(args, list)

    t_name, ext = self.m.path.splitext(self.m.path.basename(test))
    if not python_mode and self.m.platform.is_win and ext == '':
      test += '.exe'

    full_args = ['--target', self.c.build_config_fs]
    if self.m.platform.is_linux:
      full_args.append('--xvfb' if xvfb else '--no-xvfb')
    full_args += self.m.json.property_args()

    if annotate:
      full_args.append('--annotate=%s' % annotate)
      kwargs['allow_subannotations'] = True

    if annotate != 'gtest':
      assert not flakiness_dash

    if results_url:
      full_args.append('--results-url=%s' % results_url)
    if perf_dashboard_id:
      full_args.append('--perf-dashboard-id=%s' % perf_dashboard_id)
    if perf_id:
      full_args.append('--perf-id=%s' % perf_id)
    # This replaces the step_name that used to be sent via factory_properties.
    if test_type:
      full_args.append('--test-type=%s' % test_type)
    if generate_json_file:
      full_args.append('--generate-json-file')
    if results_directory:
      full_args.append('--results-directory=%s' % results_directory)
    if test_launcher_summary_output:
      full_args.extend([
        '--test-launcher-summary-output',
        test_launcher_summary_output
      ])
    if flakiness_dash:
      full_args.extend([
        '--generate-json-file',
        '-o', 'gtest-results/%s' % test,
        '--test-type', test,
      ])
      # The flakiness dashboard needs the buildnumber, so we assert it here.
      assert self.m.properties.get('buildnumber')

    # These properties are specified on every bot, so pass them down
    # unconditionally.
    full_args.append('--builder-name=%s' % self.m.properties['buildername'])
    full_args.append('--slave-name=%s' % self.m.properties['slavename'])
    # A couple of the recipes contain tests which don't specify a buildnumber,
    # so make this optional.
    if self.m.properties.get('buildnumber'):
      full_args.append('--build-number=%s' % self.m.properties['buildnumber'])
    if ext == '.py' or python_mode:
      full_args.append('--run-python-script')
    if not spawn_dbus:
      full_args.append('--no-spawn-dbus')
    if parallel:
      full_args.append('--parallel')
    if revision:
      full_args.append('--revision=%s' % revision)
    if webkit_revision:
      full_args.append('--webkit-revision=%s' % webkit_revision)
    # The master_class_name is normally computed by runtest.py itself.
    # The only reason it is settable via this API is to enable easier
    # local testing of recipes. Be very careful when passing this
    # argument.
    if master_class_name:
      full_args.append('--master-class-name=%s' % master_class_name)

    if self.c.memory_tool:
      full_args.extend([
        '--pass-build-dir',
        '--pass-target',
        '--run-shell-script',
        self.c.memory_tests_runner,
        '--test', test,
        '--tool', self.c.memory_tool,
      ])
    else:
      full_args.append(test)

    full_args.extend(args)

    # By default, always run the tests.
    kwargs.setdefault('always_run', True)

    return self.m.python(
      name or t_name,
      self.m.path['build'].join('scripts', 'slave', 'runtest.py'),
      full_args,
      **kwargs
    )

  @property
  def is_release_build(self):
    return self.c.BUILD_CONFIG == 'Release'

  def run_telemetry_test(self, runner, test, name='', args=None,
                         prefix_args=None, results_directory='',
                         spawn_dbus=False, revision=None, webkit_revision=None,
                         master_class_name=None):
    """Runs a Telemetry based test with 'runner' as the executable.
    Automatically passes certain flags like --output-format=gtest to the
    test runner. 'prefix_args' are passed before the built-in arguments and
    'args'."""
    # Choose a reasonable default for the location of the sandbox binary
    # on the bots.
    env = {}
    if self.m.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = self.m.path.join(
        '/opt', 'chromium', 'chrome_sandbox')

    if not name:
      name = test

    # The step name must end in 'test' or 'tests' in order for the results to
    # automatically show up on the flakiness dashboard.
    if not (name.endswith('test') or name.endswith('tests')):
      name = '%s_tests' % name

    test_args = []
    if prefix_args:
      test_args.extend(prefix_args)
    test_args.extend([test,
                      '--show-stdout',
                      '--output-format=gtest',
                      '--browser=%s' % self.c.BUILD_CONFIG.lower()])
    if args:
      test_args.extend(args)

    if not results_directory:
      results_directory = self.m.path['slave_build'].join('gtest-results', name)

    return self.runtest(
        runner,
        test_args,
        annotate='gtest',
        name=name,
        test_type=name,
        generate_json_file=True,
        results_directory=results_directory,
        python_mode=True,
        spawn_dbus=spawn_dbus,
        revision=revision,
        webkit_revision=webkit_revision,
        master_class_name=master_class_name,
        env=env)

  def run_telemetry_unittests(self):
    return self.runtest(
        self.m.path['checkout'].join('tools', 'telemetry', 'run_tests'),
        args=['--browser=%s' % self.c.build_config_fs.lower()],
        annotate='gtest',
        name='telemetry_unittests',
        test_type='telemetry_unittests',
        python_mode=True,
        xvfb=True)

  def run_telemetry_perf_unittests(self):
    return self.runtest(
        self.m.path['checkout'].join('tools', 'perf', 'run_tests'),
        args=['--browser=%s' % self.c.build_config_fs.lower()],
        annotate='gtest',
        name='telemetry_perf_unittests',
        test_type='telemetry_perf_unittests',
        python_mode=True,
        xvfb=True)

  def runhooks(self, run_gyp=True, **kwargs):
    """Run the build-configuration hooks for chromium."""
    env = kwargs.get('env', {})
    if run_gyp:
      env.update(self.c.gyp_env.as_jsonish())
    else:
      env['GYP_CHROMIUM_NO_ACTION'] = 1
    kwargs['env'] = env
    return self.m.gclient.runhooks(**kwargs)

  def run_gn(self):
    gn_args = []
    if self.c.BUILD_CONFIG == 'Debug':
      gn_args.append('is_debug=true')
    if self.c.BUILD_CONFIG == 'Release':
      gn_args.append('is_debug=false')
    if self.c.TARGET_PLATFORM == 'android':
      gn_args.append('os="android"')
    if self.c.TARGET_ARCH == 'arm':
      gn_args.append('cpu_arch="arm"')

    return self.m.python(
        name='gn',
        script=self.m.path['depot_tools'].join('gn.py'),
        args=[
            '--root=%s' % str(self.m.path['checkout']),
            'gen',
            '//out/%s' % self.c.BUILD_CONFIG,
            '--args=%s' % ' '.join(gn_args),
        ])

  def taskkill(self):
    return self.m.python(
      'taskkill',
      self.m.path['build'].join('scripts', 'slave', 'kill_processes.py'))

  def cleanup_temp(self):
    return self.m.python(
      'cleanup_temp',
      self.m.path['build'].join('scripts', 'slave', 'cleanup_temp.py'))

  def archive_build(self, step_name, gs_bucket, **kwargs):
    """Returns a step invoking archive_build.py to archive a Chromium build."""

    # archive_build.py insists on inspecting factory properties. For now just
    # provide these options in the format it expects.
    fake_factory_properties = {
        'gclient_env': self.c.gyp_env.as_jsonish(),
        'gs_bucket': 'gs://%s' % gs_bucket,
    }

    args = [
        '--target', self.c.BUILD_CONFIG,
        '--factory-properties', self.m.json.dumps(fake_factory_properties),
    ]
    return self.m.python(
      step_name,
      self.m.path['build'].join('scripts', 'slave', 'chromium',
                                'archive_build.py'),
      args,
      **kwargs)

  def checkdeps(self, suffix=None, **kwargs):
    name = 'checkdeps'
    if suffix:
      name += ' (%s)' % suffix
    return self.m.python(
        name,
        self.m.path['checkout'].join('tools', 'checkdeps', 'checkdeps.py'),
        args=['--json', self.m.json.output()],
        step_test_data=lambda: self.m.json.test_api.output([]),
        **kwargs)

  def checkperms(self, **kwargs):
    return self.m.python(
        'checkperms',
        self.m.path['checkout'].join('tools', 'checkperms', 'checkperms.py'),
        args=['--root', self.m.path['checkout']],
        **kwargs)

  def deps2git(self, suffix=None, **kwargs):
    name = 'deps2git'
    if suffix:
      name += ' (%s)' % suffix
    return self.m.python(
        name,
        self.m.path['checkout'].join('tools', 'deps2git', 'deps2git.py'),
        args=['-d', self.m.path['checkout'].join('DEPS'),
              '-o', self.m.path['checkout'].join('.DEPS.git'),
              '--verify',
              '--json', self.m.json.output()],
        step_test_data=lambda: self.m.json.test_api.output([]),
        **kwargs)

  def deps2submodules(self, **kwargs):
    return self.m.python(
        'deps2submodules',
        self.m.path['checkout'].join('tools', 'deps2git', 'deps2submodules.py'),
        args=['--gitless', self.m.path['checkout'].join('.DEPS.git')],
        **kwargs)
