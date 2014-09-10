# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave import recipe_util

from . import builders
from . import steps

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
  def __init__(self, *args, **kwargs):
    super(ChromiumApi, self).__init__(*args, **kwargs)
    self._build_properties = None

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

      'BUILD_CONFIG': self.m.properties.get('build_config', 'Release'),
    }

  @property
  def builders(self):
    return builders.BUILDERS

  @property
  def steps(self):
    return steps

  @property
  def build_properties(self):
    return self._build_properties

  @property
  def output_dir(self):
    """Return the path to the built executable directory."""
    return self.c.build_dir.join(self.c.build_config_fs)

  @property
  def version(self):
    """Returns a version dictionary (after get_version()), e.g.

    { 'MAJOR'": '37', 'MINOR': '0', 'BUILD': '2021', 'PATCH': '0' }
    """
    text = self._version
    output = {}
    for line in text.splitlines():
      [k,v] = line.split('=', 1)
      output[k] = v
    return output

  def get_version(self):
    self._version = self.m.step(
        'get version',
        ['cat', self.m.path['checkout'].join('chrome', 'VERSION')],
        stdout=self.m.raw_io.output('version'),
        step_test_data=(
            lambda: self.m.raw_io.test_api.stream_output(
                "MAJOR=37\nMINOR=0\nBUILD=2021\nPATCH=0\n"))).stdout
    return self.version

  def set_build_properties(self, props):
    self._build_properties = props

  def compile(self, targets=None, name=None,
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
    if self.c.compile_py.cross_tool:
      args += ['--crosstool', self.c.compile_py.cross_tool]
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
    if self.c.compile_py.build_tool == 'xcode':
      for target in targets:
        args.extend(['-target', target])
      if self.c.compile_py.xcode_sdk:
        args.extend(['-sdk', self.c.compile_py.xcode_sdk])
    else:
      args.extend(targets)
    self.m.python(name or 'compile',
                  self.m.path['build'].join('scripts', 'slave',
                                            'compile.py'),
                  args, **kwargs)

  @recipe_util.returns_placeholder
  def test_launcher_filter(self, tests):
    return TestLauncherFilterFileInputPlaceholder(self, tests)

  def runtest(self, test, args=None, xvfb=False, name=None, annotate=None,
              results_url=None, perf_dashboard_id=None, test_type=None,
              generate_json_file=False, results_directory=None,
              python_mode=False, spawn_dbus=True, parallel=False,
              revision=None, webkit_revision=None, master_class_name=None,
              test_launcher_summary_output=None, flakiness_dash=None,
              perf_id=None, perf_config=None, **kwargs):
    """Return a runtest.py invocation."""
    args = args or []
    assert isinstance(args, list)

    t_name, ext = self.m.path.splitext(self.m.path.basename(test))
    if not python_mode and self.m.platform.is_win and ext == '':
      test += '.exe'

    full_args = ['--target', self.c.build_config_fs]
    if self.c.TARGET_PLATFORM == 'ios':
      full_args.extend(['--test-platform', 'ios-simulator'])
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
    if perf_config:
      full_args.extend(['--perf-config', perf_config])
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
      ])
      # The flakiness dashboard needs the buildnumber, so we assert it here.
      assert self.m.properties.get('buildnumber') is not None

    # These properties are specified on every bot, so pass them down
    # unconditionally.
    full_args.append('--builder-name=%s' % self.m.properties['buildername'])
    full_args.append('--slave-name=%s' % self.m.properties['slavename'])
    # A couple of the recipes contain tests which don't specify a buildnumber,
    # so make this optional.
    if self.m.properties.get('buildnumber') is not None:
      full_args.append('--build-number=%s' % self.m.properties['buildnumber'])
    if ext == '.py' or python_mode:
      full_args.append('--run-python-script')
    if not spawn_dbus:
      full_args.append('--no-spawn-dbus')
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

    if self.c.gyp_env.GYP_DEFINES.get('asan', 0) == 1:
      full_args.append('--enable-asan')
    if self.c.gyp_env.GYP_DEFINES.get('lsan', 0) == 1:  # pragma: no cover
      full_args.append('--enable-lsan')
      full_args.append('--lsan-suppressions-file=%s' %
                       self.c.runtests.lsan_suppressions_file)
    if self.c.gyp_env.GYP_DEFINES.get('msan', 0) == 1:
      full_args.append('--enable-msan')
    if self.c.gyp_env.GYP_DEFINES.get('tsan', 0) == 1:
      full_args.append('--enable-tsan')
    if self.c.gyp_env.GYP_DEFINES.get('syzyasan', 0) == 1:
      full_args.append('--use-syzyasan-logger')
    if self.c.runtests.memory_tool:
      full_args.extend([
        '--pass-build-dir',
        '--pass-target',
        '--run-shell-script',
        self.c.runtests.memory_tests_runner,
        '--test', t_name,
        '--tool', self.c.runtests.memory_tool,
      ])
    else:
      full_args.append(test)

    full_args.extend(self.c.runtests.test_args)
    full_args.extend(args)

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
                         master_class_name=None, **kwargs):
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
        env=env,
        **kwargs)

  def run_telemetry_unittests(self, suffix=None, cmd_args=None, **kwargs):
    return self._run_telemetry_script(
        'telemetry_unittests',
        self.m.path['checkout'].join('tools', 'telemetry', 'run_tests'),
        suffix, cmd_args, **kwargs)

  def run_telemetry_perf_unittests(self, suffix=None, cmd_args=None, **kwargs):
    return self._run_telemetry_script(
        'telemetry_perf_unittests',
        self.m.path['checkout'].join('tools', 'perf', 'run_tests'),
        suffix, cmd_args, **kwargs)

  def _run_telemetry_script(self, name, script_path, suffix,
                            cmd_args, **kwargs):
    test_type = name
    if suffix:
      name += ' (%s)' % suffix
    cmd_args = cmd_args or []

    args = ['--browser=%s' % self.c.build_config_fs.lower(),
            '--retry-limit=3']

    if not self.m.tryserver.is_tryserver:
      chromium_revision = self.m.bot_update.properties['got_revision']
      blink_revision = self.m.bot_update.properties['got_webkit_revision']
      args += [
          '--builder-name=%s' % self.m.properties['buildername'],
          '--master-name=%s' % self.m.properties['mastername'],
          '--test-results-server=%s' % 'test-results.appspot.com',
          '--test-type=%s' % test_type,
          '--metadata', 'chromium_revision=%s' % chromium_revision,
          '--metadata', 'blink_revision=%s' % blink_revision,
          '--metadata', 'build_number=%s' % self.m.properties['buildnumber'],
      ]

    args += cmd_args

    return self.runtest(
        script_path,
        args=args,
        annotate='gtest',
        name=name,
        test_type=test_type,
        python_mode=True,
        xvfb=True,
        **kwargs)

  def runhooks(self, **kwargs):
    """Run the build-configuration hooks for chromium."""
    env = kwargs.get('env', {})
    if self.c.project_generator.tool == 'gyp':
      env.update(self.c.gyp_env.as_jsonish())
    else:
      env['GYP_CHROMIUM_NO_ACTION'] = 1
    kwargs['env'] = env
    self.m.gclient.runhooks(**kwargs)

  def run_gn(self, use_goma=False):
    gn_args = []
    if self.c.BUILD_CONFIG == 'Debug':
      gn_args.append('is_debug=true')
    if self.c.BUILD_CONFIG == 'Release':
      gn_args.append('is_debug=false')
    if self.c.TARGET_PLATFORM == 'android':
      gn_args.append('os="android"')
    if self.c.TARGET_ARCH == 'arm':
      gn_args.append('cpu_arch="arm"')

    # TODO: crbug.com/395784.
    # Consider getting the flags to use via the project_generator config
    # and/or modifying the goma config to modify the gn flags directly,
    # rather than setting the gn_args flags via a parameter passed to
    # run_gn(). We shouldn't have *three* different mechanisms to control
    # what args to use.
    if use_goma:
      gn_args.append('use_goma=true')
      gn_args.append('goma_dir="%s"' % self.m.path['build'].join('goma'))
    gn_args.extend(self.c.project_generator.args)

    self.m.python(
        name='gn',
        script=self.m.path['depot_tools'].join('gn.py'),
        args=[
            '--root=%s' % str(self.m.path['checkout']),
            'gen',
            '//out/%s' % self.c.BUILD_CONFIG,
            '--args=%s' % ' '.join(gn_args),
        ])

  def taskkill(self):
    self.m.python(
      'taskkill',
      self.m.path['build'].join('scripts', 'slave', 'kill_processes.py'))

  def cleanup_temp(self):
    self.m.python(
      'cleanup_temp',
      self.m.path['build'].join('scripts', 'slave', 'cleanup_temp.py'))

  def crash_handler(self):
    self.m.python(
        'start_crash_service',
        self.m.path['build'].join('scripts', 'slave', 'chromium',
                                  'run_crash_handler.py'),
        ['--target', self.c.build_config_fs])

  def process_dumps(self, **kwargs):
    # Dumps are especially useful when other steps (e.g. tests) are failing.
    self.m.python(
        'process_dumps',
        self.m.path['build'].join('scripts', 'slave', 'process_dumps.py'),
        ['--target', self.c.build_config_fs],
        **kwargs)

  def apply_syzyasan(self):
    args = ['--target', self.c.BUILD_CONFIG]
    self.m.python(
      'apply_syzyasan',
      self.m.path['build'].join('scripts', 'slave', 'chromium',
                                'win_apply_syzyasan.py'),
      args)

  def archive_build(self, step_name, gs_bucket, gs_acl=None, **kwargs):
    """Returns a step invoking archive_build.py to archive a Chromium build."""

    # archive_build.py insists on inspecting factory properties. For now just
    # provide these options in the format it expects.
    fake_factory_properties = {
        'gclient_env': self.c.gyp_env.as_jsonish(),
        'gs_bucket': 'gs://%s' % gs_bucket,
    }
    if gs_acl is not None:
      fake_factory_properties['gs_acl'] = gs_acl

    args = [
        '--target', self.c.BUILD_CONFIG,
        '--factory-properties', self.m.json.dumps(fake_factory_properties),
    ]
    if self.build_properties:
      args += [
        '--build-properties', self.m.json.dumps(self.build_properties),
      ]
    self.m.python(
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
        self.m.path['checkout'].join('buildtools', 'checkdeps', 'checkdeps.py'),
        args=['--json', self.m.json.output()],
        step_test_data=lambda: self.m.json.test_api.output([]),
        **kwargs)

  def checkperms(self, suffix=None, **kwargs):
    name = 'checkperms'
    if suffix:
      name += ' (%s)' % suffix
    return self.m.python(
        name,
        self.m.path['checkout'].join('tools', 'checkperms', 'checkperms.py'),
        args=[
            '--root', self.m.path['checkout'],
            '--json', self.m.json.output(),
        ],
        step_test_data=lambda: self.m.json.test_api.output([]),
        **kwargs)

  def checklicenses(self, suffix=None, **kwargs):
    name = 'checklicenses'
    if suffix:
      name += ' (%s)' % suffix
    return self.m.python(
        name,
        self.m.path['checkout'].join(
            'tools', 'checklicenses', 'checklicenses.py'),
        args=[
            '--root', self.m.path['checkout'],
            '--json', self.m.json.output(),
        ],
        step_test_data=lambda: self.m.json.test_api.output([]),
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

  def list_perf_tests(self, browser, num_shards, devices=[]):
    args = ['list', '--browser', browser, '--json-output',
            self.m.json.output(), '--num-shards', num_shards]
    for x in devices:
      args += ['--device', x]

    return self.m.python(
      'List Perf Tests',
      self.m.path['checkout'].join('tools', 'perf', 'run_benchmark'),
      args,
      step_test_data=lambda: self.m.json.test_api.output({
        "steps": {
          "blink_perf.all": {
            "cmd": "cmd1",
            "device_affinity": 0
          },
          "dromaeo.cssqueryjquery": {
            "cmd": "cmd2",
            "device_affinity": 1
          },
        },
        "version": 1,
      }))

  def get_annotate_by_test_name(self, test_name):
    if test_name.split('.')[0] == 'page_cycler':
      return 'pagecycler'
    elif test_name.split('.')[0] == 'endure':
      return 'endure'
    return 'graphing'

  def get_vs_toolchain_if_necessary(self):
    """Updates and/or installs the Visual Studio toolchain if necessary.
    Used on Windows bots which only run tests and do not check out the
    Chromium workspace. Has no effect on non-Windows platforms."""
    # These hashes come from src/build/toolchain_vs2013.hash in the
    # Chromium workspace.
    if self.m.platform.is_win:
      self.m.python(
          name='get_vs_toolchain_if_necessary',
          script=self.m.path['depot_tools'].join(
              'win_toolchain', 'get_toolchain_if_necessary.py'),
          args=[
              '27eac9b2869ef6c89391f305a3f01285ea317867',
              '9d9a93134b3eabd003b85b4e7dea06c0eae150ed',
          ])
