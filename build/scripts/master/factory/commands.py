# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory (BuildFactory).

All the utility functions to add steps to a build factory here are not
project-specific. See the other *_commands.py for project-specific commands.
"""

import json
import ntpath
import posixpath
import re

from buildbot.locks import SlaveLock
from buildbot.process.properties import WithProperties
from buildbot.status.builder import SUCCESS
from buildbot.steps import shell
from buildbot.steps.transfer import FileDownload
from twisted.python import log

from common import chromium_utils
import config

from master import chromium_step
from master.log_parser import retcode_command
from master.optional_arguments import ListProperties


# DEFAULT_TESTS is a marker to specify that the default tests should be run for
# this builder. It's mainly used for try job; this is implicit for non-try
# builders that all steps are run.
DEFAULT_TESTS = 'defaulttests'


# Performance step utils.
def CreatePerformanceStepClass(
    log_processor_class, report_link=None, output_dir=None,
    factory_properties=None, perf_name=None, test_name=None,
    command_class=None):
  """Returns ProcessLogShellStep class.

  Args:
    log_processor_class: class that will be used to process logs. Normally
      should be a subclass of process_log.PerformanceLogProcessor.
    report_link: URL that will be used as a link to results. If None,
      result won't be written into file.
    output_dir: directory where the log processor will write the results.
    command_class: command type to run for this step. Normally this will be
      chromium_step.ProcessLogShellStep.
  """
  factory_properties = factory_properties or {}
  command_class = command_class or chromium_step.ProcessLogShellStep
  # We create a log-processor class using
  # chromium_utils.InitializePartiallyWithArguments, which uses function
  # currying to create classes that have preset constructor arguments.
  # This serves two purposes:
  # 1. Allows the step to instantiate its log processor without any
  #    additional parameters;
  # 2. Creates a unique log processor class for each individual step, so
  # they can keep state that won't be shared between builds
  log_processor_class = chromium_utils.InitializePartiallyWithArguments(
      log_processor_class, report_link=report_link, output_dir=output_dir,
      factory_properties=factory_properties, perf_name=perf_name,
      test_name=test_name)
  # Similarly, we need to allow buildbot to create the step itself without
  # using additional parameters, so we create a step class that already
  # knows which log_processor to use.
  return chromium_utils.InitializePartiallyWithArguments(
      command_class, log_processor_class=log_processor_class)


class RunHooksShell(shell.ShellCommand):
  """A special run hooks shell command to allow modifying its environment
  right before it starts up."""
  def setupEnvironment(self, cmd):
    try:
      test_filters = self.getProperty('testfilter')
    except KeyError:
      test_filters = None
    test_filters = test_filters or DEFAULT_TESTS

    # If swarm tests are present ensure that the hash output required
    # by them is generated.
    if any(test.endswith('_swarm') or '_swarm:' in test
           for test in test_filters):
      environ = cmd.args.get('env', {}).copy()
      environ.setdefault('GYP_DEFINES', '')
      environ['GYP_DEFINES'] += ' test_isolation_mode=hashtable'
      environ['GYP_DEFINES'] += (' test_isolation_outdir=' +
                                 config.Master.swarm_hashtable_server_internal)


      cmd.args['env'] = environ

    shell.ShellCommand.setupEnvironment(self, cmd)


class SwarmShellForHashes(shell.ShellCommand):
  """A basic swarm ShellCommand wrapper that assumes the script it runs will
  output a list of property names and hashvalues, with each pair on its own
  line."""
  def commandComplete(self, cmd):
    shell.ShellCommand.commandComplete(self, cmd)

    re_hash_mapping = re.compile(r'^([a-z_]+) ([0-9a-f]{40})$')
    matches = (
        re_hash_mapping.match(l.strip()) for l in self.stdio_log.readlines())
    swarm_hashes = dict(x.groups() for x in matches if x)

    self.setProperty('swarm_hashes', swarm_hashes)


def GetSwarmTestsFromTestFilter(test_filters):
  """Returns a list of all the tests in the list that should be run with
  swarm."""
  swarm_tests = []
  for test_filter in test_filters:
    if '_swarm:' in test_filter:
      swarm_tests.append(test_filter.split('_swarm:', 1)[0])
    elif test_filter.endswith('_swarm'):
      swarm_tests.append(test_filter[:-len('_swarm')])

  return swarm_tests


class CompileWithRequiredSwarmTargets(shell.Compile):
  def start(self):
    try:
      test_filters = self.getProperty('testfilter')
    except KeyError:
      test_filters = []

    command = self.command
    swarm_tests = GetSwarmTestsFromTestFilter(test_filters)
    command.extend(swarm_test + '_run' for swarm_test in swarm_tests)
    if 'compile' in test_filters and not 'All' in command:
      # ninja has an 'all' pseudo-target that tries to run all the targets knows
      # about.
      # 'All' is a target in build/all.gyp that contains the vast majority of
      # targets but not all of them. :)
      command.append('All')

    self.setCommand(command)
    return shell.Compile.start(self)


class FactoryCommands(object):
  # Base URL for performance test results.
  PERF_BASE_URL = config.Master.perf_base_url
  PERF_REPORT_URL_SUFFIX = config.Master.perf_report_url_suffix

  # Directory in which to save perf output data files.
  PERF_OUTPUT_DIR = config.Master.perf_output_dir

  # Use this to prevent steps which cannot be run on the same
  # slave from being done together (in the case where slaves are
  # shared by multiple builds).
  slave_exclusive_lock = SlaveLock('slave_exclusive', maxCount=1)

  # --------------------------------------------------------------------------
  # PERF TEST SETTINGS
  # In each mapping below, the first key is the target and the second is the
  # perf_id. The value is the directory name in the results URL.

  # Configuration of most tests.
  PERF_TEST_MAPPINGS = {
    'Release': {
      'chrome-linux32-beta': 'linux32-beta',
      'chrome-linux32-stable': 'linux32-stable',
      'chrome-linux64-beta': 'linux64-beta',
      'chrome-linux64-stable': 'linux64-stable',
      'chrome-mac-beta': 'mac-beta',
      'chrome-mac-stable': 'mac-stable',
      'chrome-win-beta': 'win-beta',
      'chrome-win-stable': 'win-stable',
      'chromium-linux-targets': 'linux-targets',
      'chromium-mac-targets': 'mac-targets',
      'chromium-rel-frame': 'win-release-chrome-frame',
      'chromium-rel-linux': 'linux-release',
      'chromium-rel-linux-64': 'linux-release-64',
      'chromium-rel-linux-hardy': 'linux-release-hardy',
      'chromium-rel-linux-hardy-lowmem': 'linux-release-lowmem',
      'chromium-rel-linux-memory': 'linux-release-memory',
      'chromium-rel-linux-webkit': 'linux-release-webkit-latest',
      'chromium-rel-mac': 'mac-release',
      'chromium-rel-mac-memory': 'mac-release-memory',
      'chromium-rel-mac5': 'mac-release-10.5',
      'chromium-rel-mac6': 'mac-release-10.6',
      'chromium-rel-mac5-v8': 'mac-release-10.5-v8-latest',
      'chromium-rel-mac6-v8': 'mac-release-10.6-v8-latest',
      'chromium-rel-mac6-webkit': 'mac-release-10.6-webkit-latest',
      'chromium-rel-old-mac6': 'mac-release-old-10.6',
      'chromium-rel-vista-dual': 'vista-release-dual-core',
      'chromium-rel-vista-dual-v8': 'vista-release-v8-latest',
      'chromium-rel-vista-memory': 'vista-release-memory',
      'chromium-rel-vista-single': 'vista-release-single-core',
      'chromium-rel-vista-webkit': 'vista-release-webkit-latest',
      'chromium-rel-xp': 'xp-release',
      'chromium-rel-xp-dual': 'xp-release-dual-core',
      'chromium-rel-xp-single': 'xp-release-single-core',
      'chromium-win-targets': 'win-targets',
      'o3d-mac-experimental': 'o3d-mac-experimental',
      'o3d-win-experimental': 'o3d-win-experimental',
      'nacl-lucid64-spec-x86': 'nacl-lucid64-spec-x86',
      'nacl-lucid64-spec-arm': 'nacl-lucid64-spec-arm',
      'nacl-lucid64-spec-trans': 'nacl-lucid64-spec-trans',
    },
    'Debug': {
      'chromium-dbg-linux': 'linux-debug',
      'chromium-dbg-mac': 'mac-debug',
      'chromium-dbg-xp': 'xp-debug',
      'chromium-dbg-linux-try': 'linux-try-debug',
    },
  }

  DEFAULT_GTEST_FILTER = ''
  # TODO(maruel): DEFAULT_GTEST_FILTER = '-*.FLAKY_*:*.FAILS_*'

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None):
    """Initializes the SlaveCommands class.
    Args:
      factory: BuildFactory to configure.
      target: Build configuration, case-sensitive; probably 'Debug' or
          'Release'
      build_dir: name of the directory within the buildbot working directory
        in which the solution, Debug, and Release directories are found.
      target_platform: Slave's OS.
    """

    self._factory = factory
    self._target = target
    self._build_dir = build_dir
    self._target_platform = target_platform
    self._target_arch = target_arch

    # Starting from e.g. C:\b\build\slave\build_slave_path\build, find
    # C:\b\build\scripts\slave.
    self._script_dir = self.PathJoin('..', '..', '..', 'scripts', 'slave')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', '..', '..',
                                             'build_internal', 'scripts',
                                             'slave')

    self._perl = self.GetExecutableName('perl')

    if self._target_platform == 'win32':
      # Steps run using a separate copy of python.exe, so it can be killed at
      # the start of a build. But the kill_processes (taskkill) step has to use
      # the original python.exe, or it kills itself.
      self._python = 'python_slave'
    else:
      self._python = 'python'

    self.working_dir = 'build'
    self._repository_root = 'src'

    self._kill_tool = self.PathJoin(self._script_dir, 'kill_processes.py')
    self._compile_tool = self.PathJoin(self._script_dir, 'compile.py')
    self._test_tool = self.PathJoin(self._script_dir, 'runtest.py')
    self._zip_tool = self.PathJoin(self._script_dir, 'zip_build.py')
    self._extract_tool = self.PathJoin(self._script_dir, 'extract_build.py')
    self._cleanup_temp_tool = self.PathJoin(self._script_dir, 'cleanup_temp.py')
    self._resource_sizes_tool = self.PathJoin(self._script_dir,
                                              'resource_sizes.py')

    self._get_build_for_chromebot_tool = self.PathJoin(
        self._script_dir, 'get_build_for_chromebot.py')

    self._update_clang_tool = self.PathJoin(
        self._repository_root, 'tools', 'clang', 'scripts', 'update.sh')

    # chrome_staging directory, relative to the build directory.
    self._staging_dir = self.PathJoin('..', 'chrome_staging')

    # scripts in scripts/slave
    self._runbuild = self.PathJoin(self._script_dir, 'runbuild.py')

  # Util methods.
  def GetExecutableName(self, executable):
    """The executable name must be executable plus '.exe' on Windows, or else
    just the test name."""
    if self._target_platform == 'win32':
      return executable + '.exe'
    return executable

  def PathJoin(self, *args):
    if self._target_platform == 'win32':
      return ntpath.normpath(ntpath.join(*args))
    else:
      return posixpath.normpath(posixpath.join(*args))

  # Basic commands
  def GetTestCommand(self, executable, arg_list=None, factory_properties=None,
                     test_tool_arg_list=None):
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]
    if executable in ('performance_ui_tests',
                      'performance_browser_tests',
                      'sync_performance_tests'):
      cmd = self.AddBuildProperties(cmd)
      cmd = self.AddFactoryProperties(factory_properties, cmd)

    # Must add test tool arg list before test arg list.
    if test_tool_arg_list:
      cmd.extend(test_tool_arg_list)

    cmd.append(self.GetExecutableName(executable))
    if arg_list is not None:
      cmd.extend(arg_list)
    return cmd

  def GetPythonTestCommand(self, py_script, arg_list=None, wrapper_args=None):
    cmd = [self._python,
           self._test_tool,
           '--run-python-script',
           '--target', self._target,
           '--build-dir', self._build_dir]
    if wrapper_args is not None:
      cmd.extend(wrapper_args)
    cmd.append(py_script)

    if arg_list is not None:
      cmd.extend(arg_list)
    return cmd

  def GetShellTestCommand(self, sh_script, arg_list=None, wrapper_args=None,
                          factory_properties=None):
    """ As above, arg_list goes to the shell script, wrapper_args come
        before the script so the test tool uses them.
    """
    cmd = [self._python,
           self._test_tool,
           '--run-shell-script',
           '--target', self._target,
           '--build-dir', self._build_dir]
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    if wrapper_args is not None:
      cmd.extend(wrapper_args)
    cmd.append(sh_script)
    if arg_list is not None:
      cmd.extend(arg_list)
    return cmd

  def AddBuildProperties(self, cmd=None):
    """Adds a WithProperties() call with build properties to cmd."""
    # pylint: disable=R0201
    cmd = cmd or []

    # Create a WithProperties format string that includes build properties.
    build_properties = dict(
        (prop, '%%(%s:-)s' % prop)
        for prop in (
            'blamelist', 'branch', 'buildername', 'buildnumber', 'got_revision',
            'mastername', 'parentname', 'parentslavename', 'parent_buildnumber',
            'parent_builddir', 'revision', 'scheduler', 'slavename',
        )
    )

    def gen_blamelist_string(build):
      blame = ','.join(build.getProperty('blamelist'))
      # Could be interpreted by the shell.
      return re.sub(r'[\&\|\^]', '', blame.replace('<', '[').replace('>', ']'))
    # The |separators| argument is to densify the command line.
    string = '--build-properties=' + json.dumps(
        build_properties, sort_keys=True, separators=(',', ':'))
    cmd.append(WithProperties(string, blamelist=gen_blamelist_string))
    return cmd

  def AddFactoryProperties(self, factory_properties, cmd=None):
    """Adds factory properties to cmd."""
    # pylint: disable=R0201
    cmd = cmd or []
    cmd.append(
        '--factory-properties=' + json.dumps(
            factory_properties or {}, sort_keys=True, separators=(',', ':')))
    return cmd

  def AddTestStep(self, command_class, test_name, test_command,
                  test_description='', timeout=10*60, max_time=8*60*60,
                  workdir=None, env=None, locks=None, halt_on_failure=False,
                  do_step_if=True, br_do_step_if=False, hide_step_if=False,
                  **kwargs):
    """Adds a step to the factory to run a test.

    Args:
      command_class: the command type to run, such as shell.ShellCommand
      test_name: a string describing the test, used to build its logfile name
          and its descriptions in the waterfall display
      timeout: the buildbot timeout for the test, in seconds.  If it doesn't
          produce any output to stdout or stderr for this many seconds,
          buildbot will cancel it and call it a failure.
      max_time: the maxiumum time the command can run, in seconds.  If the
          command doesn't return in this many seconds, buildbot will cancel it
          and call it a failure.
      test_command: the command list to run
      test_description: an auxiliary description to be appended to the
        test_name in the buildbot display; for example, ' (single process)'
      workdir: directory where the test executable will be launched. If None,
        step will use default directory.
      env: dictionary with environmental variable key value pairs that will be
        set or overridden before launching the test executable. Does not do
        anything if 'env' is None.
      locks: any locks to acquire for this test
      halt_on_failure: whether the current build should halt if this step fails
      br_do_step_if: when run under buildrunner, execute this function to
        determine whether to run a step or not. has no effect if not using
        buildrunner.
    """
    assert timeout <= max_time
    if not br_do_step_if:
      do_step_if = do_step_if or self.TestStepFilter
    else:
      # don't confuse CQ with duplicate step names
      # runbuild.py will strip this suffix out and add via annotator
      test_name +=  '_buildrunner_ignore'
    self._factory.addStep(
        command_class,
        name=test_name,
        timeout=timeout,
        maxTime=max_time,
        doStepIf=do_step_if,
        brDoStepIf=br_do_step_if,
        hideStepIf=hide_step_if,
        workdir=workdir,
        env=env,
        # TODO(bradnelson): FIXME
        #locks=locks,
        description='running %s%s' % (test_name, test_description),
        descriptionDone='%s%s' % (test_name, test_description),
        haltOnFailure=halt_on_failure,
        command=test_command,
        **kwargs)
    self._factory.properties.setProperty('gtest_filter', None, 'BuildFactory')

  def TestStepFilter(self, bStep):
    return self.TestStepFilterImpl(bStep, True)

  def TestStepFilterGTestFilterRequired(self, bStep):
    return self.TestStepFilterImpl(bStep, False)

  def TestStepFilterImpl(self, bStep, default):
    """Examines the 'testfilter' property of the build and determines if
    the step should run; True for yes."""
    # TODO(maruel): This is bad hygiene to modify the build properties on the
    # fly like this. There should be another way to communicate the command line
    # properly.
    bStep.setProperty('gtest_filter', None, 'Factory')
    if 'testfilter' not in bStep.build.getProperties():
      # Not a try job.
      return default

    filters = bStep.build.getProperties().getProperty('testfilter')
    # DEFAULT_TESTS is a marker to specify all tests should be run normally.
    # Add it if no filter is explicitly specified.
    filters = filters or [DEFAULT_TESTS]

    name = bStep.name
    # TODO(maruel): Fix the step name.
    if name.startswith('memory test: '):
      name = name[len('memory test: '):]
    filters = dict(i.split(':', 1) if ':' in i else (i, '') for i in filters)
    # Continue if:
    # - the test is specified in filters
    # - DEFAULT_TESTS is listed and default is True
    if not (name in filters or (DEFAULT_TESTS in filters and default)):
      return False

    # This is gtest specific, but other test types can safely ignore it.
    # Defaults to excluding FAILS and FLAKY test if none is specified.
    gtest_filter = filters.get(name, '') or self.DEFAULT_GTEST_FILTER
    if gtest_filter:
      flag = '--gtest_filter=%s' % gtest_filter
      bStep.setProperty('gtest_filter', flag, 'Scheduler')
    return True

  def GetTestStepFilter(self, factory_properties):
    """Returns a TestStepFilter lambda with the right default according to
    non_default factory property.
    """
    return lambda bStep: self.TestStepFilterImpl(
        bStep,
        bStep.name not in factory_properties.get('non_default', []))

  def _GTestDoStep(self, test_name, factory_properties):
    doStep = self.GetTestStepFilter(factory_properties)
    if test_name.startswith('DISABLED_'):
      test_name = test_name[len('DISABLED_'):]
      doStep = False
    return doStep

  def AddAnnotatedGTestTestStep(self, test_name, factory_properties=None,
                                description='', arg_list=None,
                                total_shards=None, shard_index=None,
                                test_tool_arg_list=None,
                                hideStep=False):
    """Adds an Annotated step to the factory to run the gtest tests.

    Args:
      test_name: If prefixed with DISABLED_ the prefix is removed, and the
                 step is flagged for not running, but is still added.
      total_shards: Number of shards to split this test into.
      shard_index: Shard to run.  Must be between 1 and total_shards.
      generate_gtest_json: generate JSON results file after running the tests.
    """

    test_tool_arg_list = test_tool_arg_list or []

    test_tool_arg_list.append('--annotate=gtest')

    factory_properties = factory_properties or {}
    generate_json = factory_properties.get('generate_gtest_json')

    if not arg_list:
      arg_list = []
    arg_list = arg_list[:]

    if not hideStep:
      doStep = self._GTestDoStep(test_name, factory_properties)
      brDoStep = False
    else:
      doStep = False
      brDoStep = lambda: self._GTestDoStep(test_name, factory_properties)

    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    # Must add test tool arg list before test arg list.
    if test_tool_arg_list:
      cmd.extend(test_tool_arg_list)

    cmd.extend(['--test-type', test_name])

    if generate_json:
      # test_result_dir (-o) specifies where we put the JSON output locally
      # on slaves.
      test_result_dir = 'gtest-results/%s' % test_name
      cmd.extend(['--generate-json-file',
                  '-o', test_result_dir,
                  '--build-number', WithProperties('%(buildnumber)s'),
                  '--builder-name', WithProperties('%(buildername)s')])

    if total_shards and shard_index:
      cmd.extend(['--total-shards', str(total_shards),
                  '--shard-index', str(shard_index)])

    if test_name in factory_properties.get('sharded_tests', []):
      cmd.append('--parallel')
      sharding_args = factory_properties.get('sharding_args')
      if sharding_args:
        cmd.extend(['--sharding-args', sharding_args])

    env = factory_properties.get('testing_env')

    cmd.append(self.GetExecutableName(test_name))

    arg_list.append('--gtest_print_time')
    arg_list.append(WithProperties('%(gtest_filter)s'))
    cmd.extend(arg_list)

    self.AddTestStep(chromium_step.AnnotatedCommand, test_name,
                     ListProperties(cmd), description, do_step_if=doStep,
                     env=env, br_do_step_if=brDoStep, hide_step_if=hideStep,
                     target=self._target, factory_properties=factory_properties)

  def AddBuildStep(self, factory_properties, name='build', env=None,
                   timeout=6000):
    """Add annotated step to use the buildrunner to run steps on the slave."""

    factory_properties['target'] = self._target

    cmd = [self._python, self._runbuild, '--annotate']
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name=name,
                          description=name,
                          timeout=timeout,
                          haltOnFailure=True,
                          command=cmd,
                          env=env,
                          factory_properties=factory_properties,
                          target=self._target)

  def AddBuildrunnerGTest(self, test_name, factory_properties=None,
                          description='', arg_list=None,
                          total_shards=None, shard_index=None,
                          test_tool_arg_list=None):
    """Add a buildrunner GTest step, which will be executed with runbuild.

    This will appear hidden and skipped on the main waterfall, but executed when
    run under runbuild.py. Note that a final runbuild step will need to be added
    with AddBuildStep().
    """
    self.AddAnnotatedGTestTestStep(test_name,
                                   factory_properties=factory_properties,
                                   description=description,
                                   arg_list=arg_list,
                                   total_shards=total_shards,
                                   shard_index=shard_index,
                                   test_tool_arg_list=test_tool_arg_list,
                                   hideStep=True)

  def AddBuildrunnerTestStep(self, command_class, test_name, test_command,
                             test_description='', timeout=10*60,
                             max_time=8*60*60, workdir=None, env=None,
                             locks=None, halt_on_failure=False,
                             do_step_if=True):
    """Add a buildrunner test step, which will be executed with runbuild.

    This will appear hidden and skipped on the main waterfall, but executed when
    run under runbuild.py. Note that a final runbuild step will need to be added
    with AddBuildStep().
    """

    do_step_if = do_step_if or self.TestStepFilter
    self.AddTestStep(command_class, test_name, test_command,
                     test_description=test_description, timeout=timeout,
                     max_time=max_time, workdir=workdir, env=env, locks=locks,
                     halt_on_failure=halt_on_failure, do_step_if=False,
                     br_do_step_if=do_step_if, hide_step_if=True)

  def AddBasicShellStep(self, test_name, timeout=600, arg_list=None):
    """Adds a step to the factory to run a simple shell test with standard
    defaults.
    """
    self.AddTestStep(shell.ShellCommand, test_name, timeout=timeout,
                     test_command=self.GetTestCommand(test_name,
                                                      arg_list=arg_list))

  # GClient related commands.
  def AddSvnKillStep(self):
    """Adds a step to the factory to kill svn.exe. Windows-only."""
    self._factory.addStep(shell.ShellCommand, name='svnkill',
                          description='svnkill', timeout=60,
                          workdir='',  # The build subdir may not exist yet.
                          command=[r'%WINDIR%\system32\taskkill',
                                   '/f', '/im', 'svn.exe',
                                   '||', 'set', 'ERRORLEVEL=0'])

  def AddTempCleanupStep(self):
    """Runs script to cleanup acculumated cruft, including tmp directory."""
    # Use ReturnCodeCommand so we can indicate a "warning" status (orange).
    self._factory.addStep(retcode_command.ReturnCodeCommand,
                          name='cleanup_temp',
                          description='cleanup_temp',
                          timeout=60,
                          workdir='',  # Doesn't really matter where we are.
                          alwaysRun=True,  # Run this even on update failures
                          command=['python', self._cleanup_temp_tool])

  def AddUpdateScriptStep(self, gclient_jobs=None, solutions=None):
    """Adds a step to the factory to update the script folder."""
    # This will be run in the '..' directory to udpate the slave's own script
    # checkout.
    command = [chromium_utils.GetGClientCommand(self._target_platform),
               'sync', '--verbose', '--force']
    if gclient_jobs:
      command.append('-j%d' % gclient_jobs)
    if solutions:
      spec = 'solutions=[%s]' % ''.join(s.GetSpec() for s in solutions)
      spec = spec.replace(' ', '')
      command.extend(['--spec', spec])
    self._factory.addStep(shell.ShellCommand,
                          name='update_scripts',
                          description='update_scripts',
                          locks=[self.slave_exclusive_lock],
                          timeout=60*5,
                          workdir='../../..',
                          command=command)

  def AddUpdateStep(self, gclient_spec, env=None, timeout=None,
                    sudo_for_remove=False, gclient_deps=None,
                    gclient_nohooks=False, no_gclient_branch=False,
                    no_gclient_revision=False,
                    gclient_transitive=False, primary_repo=None,
                    gclient_jobs=None):
    """Adds a step to the factory to update the workspace."""
    env = env or {}
    env['DEPOT_TOOLS_UPDATE'] = '0'
    if timeout is None:
      # svn timeout is 2 min; we allow 5
      timeout = 60*5
    self._factory.addStep(
        chromium_step.GClient,
        gclient_spec=gclient_spec,
        gclient_deps=gclient_deps,
        # TODO(maruel): Kept for compatibility but will be removed.
        gclient_nohooks=gclient_nohooks,
        workdir=self.working_dir,
        mode='update',
        env=env,
        locks=[self.slave_exclusive_lock],
        retry=(60*5, 4),  # Try 4+1=5 more times, 5 min apart
        timeout=timeout,
        gclient_jobs=gclient_jobs,
        sudo_for_remove=sudo_for_remove,
        rm_timeout=60*15,  # The step can take a long time.
        no_gclient_branch=no_gclient_branch,
        no_gclient_revision=no_gclient_revision,
        gclient_transitive=gclient_transitive,
        primary_repo=primary_repo)

  def AddApplyIssueStep(self, timeout, server):
    """Adds a step to the factory to apply an issues from Rietveld.

    It is a conditional step that is only run on the try server if the following
    conditions are all true:
    - There are both build properties issue and patchset
    - There is no patch attached

    Args:
      timeout: Timeout to use on the slave when running apply_issue.py.
      server: The Rietveld server to grab the patch from.
    """

    def do_step_if(bStep):
      build = bStep.build
      properties = build.getProperties()
      for prop in ('issue', 'patchset'):
        if prop not in properties or not properties.getProperty(prop):
          return False
      if build.getSourceStamp().patch:
        return False
      return True

    password = open('.apply_issue_password').readline().strip()
    self._factory.addStep(
        chromium_step.ApplyIssue,
        root=WithProperties('%(root:~src)s'),
        issue=WithProperties('%(issue:-)s'),
        patchset=WithProperties('%(patchset:-)s'),
        email='commit-bot@chromium.org',
        password=password,
        workdir=self.working_dir,
        timeout=timeout or 600,
        server=server,
        haltOnFailure=True,
        flunkOnFailure=True,
        name='apply_issue',
        doStepIf=do_step_if)

  def AddRunHooksStep(self, env=None, timeout=None):
    """Adds a step to the factory to run the gclient hooks."""
    env = env or {}
    env['LANDMINES_VERBOSE'] = '1'
    env['DEPOT_TOOLS_UPDATE'] = '0'
    if timeout is None:
      # svn timeout is 2 min; we allow 5
      timeout = 60*5
    self._factory.addStep(
        RunHooksShell,
        haltOnFailure=True,
        name='runhooks',
        description='gclient hooks',
        env=env,
        locks=[self.slave_exclusive_lock],
        timeout=timeout,
        command=['gclient', 'runhooks'])

  def AddClobberTreeStep(self, gclient_spec, env=None, timeout=None,
                         gclient_deps=None, gclient_nohooks=False,
                         no_gclient_branch=None):
    """This is not for pressing 'clobber' on the waterfall UI page. This is
       for clobbering all the sources. Using mode='clobber' causes the entire
       working directory to get moved aside (to build.dead) --OR-- if
       build.dead already exists, it deletes build.dead. Strange, but true.
       See GClient.doClobber() (for move vs. delete logic) or Gclient.start()
       (for mode='clobber' trigger) in chromium_commands.py.

       In theory, this means we can have a ClobberTree step at the beginning of
       a build to quickly move the existing workdir and do a full clean
       checkout. Then, if we add the same step at the end of a build, it will
       delete the moved-out-of-the-way directory. Presuming neither step fails
       or times out, this allows a builder to pull a full, clean tree for
       every build.

       This is exactly what we want for official release builds, so that the
       builder can refresh its entire tree based on a new buildspec (which
       might point to a completely different branch or an older revision than
       the last build on the machine).
    """
    if env is None:
      env = {}
    env['DEPOT_TOOLS_UPDATE'] = '0'
    if timeout is None:
      # svn timeout is 2 min; we allow 5
      timeout = 60*5
    self._factory.addStep(chromium_step.GClient,
                          gclient_spec=gclient_spec,
                          gclient_deps=gclient_deps,
                          gclient_nohooks=gclient_nohooks,
                          no_gclient_branch=no_gclient_branch,
                          workdir=self.working_dir,
                          mode='clobber',
                          env=env,
                          timeout=timeout,
                          rm_timeout=60*60)  # We don't care how long it takes.

  def AddTaskkillStep(self):
    """Adds a step to kill the running processes before a build."""
    # Use ReturnCodeCommand so we can indicate a "warning" status (orange).
    self._factory.addStep(retcode_command.ReturnCodeCommand, name='taskkill',
                          description='taskkill',
                          timeout=60,
                          workdir='',  # Doesn't really matter where we are.
                          command=['python', self._kill_tool])

  # Zip / Extract commands.
  def AddZipBuild(self, src_dir=None, include_files=None,
                  halt_on_failure=False, factory_properties=None):
    factory_properties = factory_properties or {}

    cmd = [self._python, self._zip_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    if 'webkit_dir' in factory_properties:
      cmd += ['--webkit-dir', factory_properties['webkit_dir']]

    if src_dir is not None:
      cmd += ['--src-dir', src_dir]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    if include_files is not None:
      # Convert the include_files array into a quoted, comma-delimited list
      # for passing as a command-line argument.
      include_arg = ','.join(include_files)
      cmd += ['--include-files', include_arg]

    self._factory.addStep(shell.ShellCommand,
                          name='package_build',
                          timeout=600,
                          description='packaging build',
                          descriptionDone='packaged build',
                          haltOnFailure=halt_on_failure,
                          command=cmd)

  def AddExtractBuild(self, build_url, factory_properties=None):
    """Extract a build.

    Assumes the zip file has a directory like src/xcodebuild which
    contains the actual build.
    """
    factory_properties = factory_properties or {}

    cmd = [self._python, self._extract_tool,
           '--build-dir', self._build_dir,
           '--target', self._target,
           '--build-url', build_url]

    if 'webkit_dir' in factory_properties:
      cmd += ['--webkit-dir', factory_properties['webkit_dir']]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self.AddTestStep(retcode_command.ReturnCodeCommand, 'extract_build', cmd,
                     halt_on_failure=True)

  def AddGetBuildForChromebot(self, platform, archive=False, extract=False,
                              build_url=None, archive_url=None, build_id=None,
                              build_dir=None):
    """Get a Chrome build for Chromebot.

    If |build_id| is omitted, latest build will be downloaded instead.

    Args:
      platform: The platform for Chrome build (win, linux, linux64).
      archive: If the |build_url| contains a list of builds.
      extract: Whether to extract the downloaded files.
      build_url: URL to the build.  Default URL if None.
      build_id: Id of build.
    """
    if not build_dir:
      build_dir = self._build_dir
    cmd = [self._python, self._get_build_for_chromebot_tool,
           '--platform', platform,
           '--build-dir', build_dir,
           '--target-dir', self._target]

    if extract:
      cmd += ['--extract']
    if build_url:
      cmd += ['--build-url', build_url]
    if archive_url:
      cmd += ['--archive-url', archive_url]

    self.AddTestStep(SetBuildPropertyShellCommand, 'get_build',
                     cmd, halt_on_failure=True)

  # Build commands.
  def GetBuildCommand(self, clobber, solution, mode, options=None):
    """Returns a command list to call the _compile_tool in the given build_dir,
    optionally clobbering the build (that is, deleting the build directory)
    first.

    if solution contains a ";", the second part is interpreted as the project.
    """
    cmd = [self._python, self._compile_tool]
    if solution:
      split_solution = solution.split(';', 1)
      cmd.extend(['--solution', split_solution[0]])
      if len(split_solution) == 2:
        cmd.extend(['--project', split_solution[1]])
    cmd.extend(['--target', self._target,
                '--build-dir', self._build_dir])
    if self._target_arch:
      cmd.extend(['--arch', self._target_arch])
    if mode:
      cmd.extend(['--mode', mode])
    if clobber:
      cmd.append('--clobber')
    else:
      # Below, WithProperties is appended to the cmd and rendered into a string
      # for each specific build at build-time.  When clobber is None, it renders
      # to an empty string.  When clobber is not None, it renders to the string
      # --clobber.  Note: the :+ after clobber controls this behavior and is not
      # a typo.
      cmd.append(WithProperties('%s', 'clobber:+--clobber'))
    if options:
      cmd.extend(options)
    # Using ListProperties will process and discard None and '' values,
    # otherwise posix platforms will fail.
    return ListProperties(cmd)

  def AddCompileStep(self, solution, clobber=False,
                     description='compiling',
                     descriptionDone='compile',
                     timeout=600, mode=None,
                     options=None, haltOnFailure=True, env=None):
    """Adds a step to the factory to compile the solution.

    Args:
      solution: the solution/sub-project file to build
      clobber: if True, clobber the build (that is, delete the build
          directory) before building
      description: for the waterfall
      descriptionDone: for the waterfall
      timeout: if no output is received in this many seconds, the compile step
          will be killed
      mode: if given, this will be passed as the --mode option to the compile
          command
      options: list of additional options to pass to the compile command
      halfOnFailure: should stop the build if compile fails
    """
    self._factory.addStep(
        CompileWithRequiredSwarmTargets,
        name='compile',
        timeout=timeout,
        description=description,
        descriptionDone=descriptionDone,
        command=self.GetBuildCommand(clobber, solution, mode, options),
        haltOnFailure=haltOnFailure,
        env=env)

  def _PerfStepMappings(self, show_results, perf_id, test_name):
    """Looks up test IDs in PERF_TEST_MAPPINGS and returns test info."""
    report_link = None
    output_dir = None
    perf_name = None

    if show_results:
      perf_name = perf_id
      if (self._target in self.PERF_TEST_MAPPINGS and
          perf_id in self.PERF_TEST_MAPPINGS[self._target]):
        perf_name = self.PERF_TEST_MAPPINGS[self._target][perf_id]
      report_link = '%s/%s/%s/%s' % (self.PERF_BASE_URL, perf_name, test_name,
                                     self.PERF_REPORT_URL_SUFFIX)
      output_dir = '%s/%s/%s' % (self.PERF_OUTPUT_DIR, perf_name, test_name)

    return report_link, output_dir, perf_name

  def GetPerfStepClass(self, factory_properties, test_name, log_processor_class,
                       command_class=None):
    """Selects the right build step for the specified perf test."""
    factory_properties = factory_properties or {}
    perf_id = factory_properties.get('perf_id')
    show_results = factory_properties.get('show_perf_results')

    report_link, output_dir, perf_name = self._PerfStepMappings(show_results,
                                                                perf_id,
                                                                test_name)

    return CreatePerformanceStepClass(log_processor_class,
        report_link=report_link, output_dir=output_dir,
        factory_properties=factory_properties, perf_name=perf_name,
        test_name=test_name, command_class=command_class)


  def AddGenerateResultHashesStep(self, using_ninja, tests=None, doStepIf=True):
    """Adds a step to generate the hashes for result files. This is used by
    swarm."""
    if using_ninja:
      out_dir = 'out'
    elif self._target_platform == 'win32':
      out_dir = 'build'
    elif self._target_platform == 'darwin':
      out_dir = 'xcodebuild'
    else:
      out_dir = 'out'

    if not self._target:
      log.msg('No target specified, unable to find result files to '
              'trigger swarm tests')
      return
    manifest_directory = self.PathJoin('src', out_dir, self._target)

    assert self._target_platform
    if self._target_platform == 'win32':
      script_path = self.PathJoin(self._script_dir, 'manifest_to_hash.bat')
    else:
      script_path = self.PathJoin(self._script_dir, 'manifest_to_hash.py')

    cmd = [script_path, '--manifest_directory', manifest_directory]
    cmd.append(tests if tests else WithProperties('%(swarm_tests:-)s'))

    self._factory.addStep(SwarmShellForHashes,
                          name='manifests_to_hashes',
                          description='manifests_to_hashes',
                          command=cmd,
                          doStepIf=doStepIf)

  # Checks out and builds clang
  def AddUpdateClangStep(self):
    cmd = [self._update_clang_tool]
    self._factory.addStep(shell.ShellCommand,
                          name='update_clang',
                          timeout=600,
                          description='Updating and building clang and plugins',
                          descriptionDone='clang updated',
                          env={'LLVM_URL': config.Master.llvm_url},
                          command=cmd)

  def AddDownloadFileStep(self, mastersrc, slavedest):
    """Download a file from master."""
    self._factory.addStep(FileDownload(mastersrc=mastersrc,
                                       slavedest=slavedest))

  def AddDiagnoseGomaStep(self):
    """Diagnose goma log."""
    goma_dir = self.PathJoin('..', '..', '..', 'goma')
    cmd = [self._python, self.PathJoin(goma_dir, 'diagnose_goma_log.py')]
    self.AddTestStep(shell.ShellCommand, 'diagnose_goma', cmd, timeout=60)


class CanCancelBuildShellCommand(shell.ShellCommand):
  """Like ShellCommand but can terminate the build.

  On failure (non-zero exit code of a shell command), this command
  will fake a success but terminate the build.  This keeps the tree
  green but otherwise stops all action.
  """

  def evaluateCommand(self, cmd):
    if cmd.rc != 0:
      reason = 'Build has been cancelled without being a failure.'
      self.build.stopBuild(reason)
      self.build.buildFinished(('Stopped Early', reason), SUCCESS)
    return SUCCESS


class WaterfallLoggingShellCommand(shell.ShellCommand):
  """A shell command that can add messages to the main waterfall page.

  Any string on stdio from this shell command with the prefix
  WATERFALL_LOG will be added to the main waterfall page.  To avoid
  pollution these should be limited and important, such as a summary
  number or version.
  """

  def __init__(self, *args, **kwargs):
    self.messages = []
    # Argh... not a new style class?
    # super(WaterfallLoggingShellCommand, self).__init__(self, *args, **kwargs)
    shell.ShellCommand.__init__(self, *args, **kwargs)

  def commandComplete(self, cmd):
    out = cmd.logs['stdio'].getText()
    self.messages = re.findall('WATERFALL_LOG (.*)', out)

  def getText(self, cmd, results):
    return self.describe(True) + self.messages


class SetBuildPropertyShellCommand(shell.ShellCommand):
  """A shell command that can set build property.

  String on stdio from this shell command will be parsed for
     BUILD_PROPERTY property_name=value
  Property name and value will be set as build property.
  """

  def __init__(self, *args, **kwargs):
    self.messages = []
    shell.ShellCommand.__init__(self, *args, **kwargs)

  def commandComplete(self, cmd):
    out = cmd.logs['stdio'].getText()
    build_properties = re.findall('BUILD_PROPERTY ([^=]*)=(.*)', out)
    for propname, value in build_properties:
      # findall can return strings containing CR characters, remove with strip.
      self.build.setProperty(propname, value.strip(), 'Step')

  def getText(self, cmd, results):
    return self.describe(True) + self.messages
