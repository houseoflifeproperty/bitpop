# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

import logging
import os
import re

from buildbot.process.properties import WithProperties
from buildbot.steps import shell
from buildbot.steps import trigger
from buildbot.steps.transfer import FileUpload

from common import chromium_utils
import config
from master import chromium_step
from master.factory import commands
from master.factory import swarm_commands

from master.log_parser import archive_command
from master.log_parser import gtest_command
from master.log_parser import process_log
from master.log_parser import retcode_command
from master.log_parser import webkit_test_command


class ChromiumCommands(commands.FactoryCommands):
  """Encapsulates methods to add chromium commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_os=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    self._target_os = target_os

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', '..', '..',
                                             'build_internal', 'scripts',
                                             'slave')

    # Create smaller name for the functions and vars to simplify the code below.
    J = self.PathJoin
    s_dir = self._chromium_script_dir
    p_dir = self._private_script_dir

    self._process_dumps_tool = self.PathJoin(self._script_dir,
                                             'process_dumps.py')

    # Scripts in the chromium scripts dir.
    self._process_coverage_tool = J(s_dir, 'process_coverage.py')
    self._layout_archive_tool = J(s_dir, 'archive_layout_test_results.py')
    self._package_source_tool = J(s_dir, 'package_source.py')
    self._crash_handler_tool = J(s_dir, 'run_crash_handler.py')
    self._upload_parity_tool = J(s_dir, 'upload_parity_data.py')
    self._target_tests_tool = J(s_dir, 'target-tests.py')
    self._layout_test_tool = J(s_dir, 'layout_test_wrapper.py')
    self._lint_test_files_tool = J(s_dir, 'lint_test_files_wrapper.py')
    self._devtools_perf_test_tool = J(s_dir, 'devtools_perf_test_wrapper.py')
    self._archive_coverage = J(s_dir, 'archive_coverage.py')
    self._gpu_archive_tool = J(s_dir, 'archive_gpu_pixel_test_results.py')
    self._crash_dump_tool = J(s_dir, 'archive_crash_dumps.py')
    self._dom_perf_tool = J(s_dir, 'dom_perf.py')
    self._asan_archive_tool = J(s_dir, 'asan_archive_build.py')
    self._archive_tool = J(s_dir, 'archive_build.py')
    self._sizes_tool = J(s_dir, 'sizes.py')
    self._check_lkgr_tool = J(s_dir, 'check_lkgr.py')
    self._windows_asan_tool = J(s_dir, 'win_apply_asan.py')

    # Scripts in the private dir.
    self._download_and_extract_official_tool = self.PathJoin(
        p_dir, 'get_official_build.py')

    # Reliability paths.
    self._reliability_tool = J(self._script_dir, 'reliability_tests.py')
    self._reliability_data = J('src', 'chrome', 'test', 'data', 'reliability')

    # These scripts should be move to the script dir.
    self._check_deps_tool = J('src', 'tools', 'checkdeps', 'checkdeps.py')
    self._check_bins_tool = J('src', 'tools', 'checkbins', 'checkbins.py')
    self._check_perms_tool = J('src', 'tools', 'checkperms', 'checkperms.py')
    self._check_licenses_tool = J('src', 'tools', 'checklicenses',
                                  'checklicenses.py')
    self._posix_memory_tests_runner = J('src', 'tools', 'valgrind',
                                        'chrome_tests.sh')
    self._win_memory_tests_runner = J('src', 'tools', 'valgrind',
                                      'chrome_tests.bat')
    self._heapcheck_tool = J('src', 'tools', 'heapcheck', 'chrome_tests.sh')
    self._nacl_integration_tester_tool = J(
        'src', 'chrome', 'test', 'nacl_test_injection',
        'buildbot_nacl_integration.py')
    # chrome_staging directory, relative to the build directory.
    self._staging_dir = self.PathJoin('..', 'chrome_staging')

    # The _update_scripts_command will be run in the _update_scripts_dir to
    # udpate the slave's own script checkout.
    self._update_scripts_dir = '..'
    self._update_scripts_command = [
        chromium_utils.GetGClientCommand(self._target_platform),
        'sync', '--verbose']

  def AddArchiveStep(self, data_description, base_url, link_text, command,
                     more_link_url=None, more_link_text=None,
                     index_suffix=''):
    step_name = ('archive_%s' % data_description).replace(' ', '_')
    self._factory.addStep(archive_command.ArchiveCommand,
                          name=step_name,
                          timeout=600,
                          description='archiving %s' % data_description,
                          descriptionDone='archived %s' % data_description,
                          base_url=base_url,
                          link_text=link_text,
                          more_link_url=more_link_url,
                          more_link_text=more_link_text,
                          command=command,
                          index_suffix=index_suffix)

  def AddUploadPerfExpectations(self, factory_properties=None):
    """Adds a step to the factory to upload perf_expectations.json to the
    master.
    """
    perf_id = factory_properties.get('perf_id')
    if not perf_id:
      logging.error('Error: cannot upload perf expectations: perf_id is unset')
      return
    slavesrc = 'src/tools/perf_expectations/perf_expectations.json'
    masterdest = ('../../scripts/master/log_parser/perf_expectations/%s.json' %
                  perf_id)

    self._factory.addStep(FileUpload(slavesrc=slavesrc,
                                     masterdest=masterdest))

  def AddWindowsASANStep(self):
    """Adds a step to run syzygy/ASAN over the output directory."""
    cmd = [self._python, self._windows_asan_tool,
           '--build-dir', self._build_dir, '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'apply_asan', cmd)

  def AddArchiveBuild(self, mode='dev', show_url=True, factory_properties=None):
    """Adds a step to the factory to archive a build."""

    extra_archive_paths = factory_properties.get('extra_archive_paths')
    use_build_number = factory_properties.get('use_build_number', False)

    if show_url:
      (url, index_suffix) = _GetSnapshotUrl(factory_properties)
      text = 'download'
    else:
      url = None
      index_suffix = None
      text = None

    cmd = [self._python, self._archive_tool,
           '--target', self._target,
           '--build-dir', self._build_dir,
           '--mode', mode]
    if extra_archive_paths:
      cmd.extend(['--extra-archive-paths', extra_archive_paths])
    if use_build_number:
      cmd.extend(['--build-number', WithProperties('%(buildnumber)s')])

    gclient_env = (factory_properties or {}).get('gclient_env', {})
    if 'target_arch=arm' in gclient_env.get('GYP_DEFINES', ''):
      cmd.extend(['--arch', 'arm'])

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self.AddArchiveStep(data_description='build', base_url=url, link_text=text,
                        command=cmd, index_suffix=index_suffix)

  def AddAsanArchiveBuild(self, factory_properties=None):
    """Adds a step to the factory to archive an asan build."""

    cmd = [self._python, self._asan_archive_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self.AddTestStep(retcode_command.ReturnCodeCommand, 'ASAN Archive', cmd)

  def AddPackageSource(self, factory_properties=None):
    """Adds a step to the factory to package and upload the source directory."""
    factory_properties = factory_properties or {}
    factory_properties.setdefault('package_filename', 'chromium-src.tar.bz2')

    cmd = [self._python, self._package_source_tool]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self._factory.addStep(archive_command.ArchiveCommand,
                          name='package_source',
                          timeout=1200,
                          description='packaging source',
                          descriptionDone='packaged source',
                          base_url=None,
                          link_text=None,
                          more_link_url=None,
                          more_link_text=None,
                          command=cmd)

  def GetAnnotatedPerfCmd(self, gtest_filter, log_type, test_name,
                          cmd_name='performance_ui_tests', tool_opts=None,
                          options=None, factory_properties=None):
    """Return a runtest command suitable for most perf test steps."""

    tool_options = ['--annotate=' + log_type]
    tool_options += tool_opts or []

    arg_list = options or []
    if gtest_filter:
      arg_list += ['--gtest_filter=' + gtest_filter]

    factory_properties = factory_properties or {}
    factory_properties['test_name'] = test_name

    perf_id = factory_properties.get('perf_id')
    show_results = factory_properties.get('show_perf_results')

    _, _, perf_name = self._PerfStepMappings(show_results,
                                             perf_id,
                                             test_name)
    factory_properties['perf_name'] = perf_name

    return self.GetTestCommand(cmd_name, test_tool_arg_list=tool_options,
                               arg_list=arg_list,
                               factory_properties=factory_properties)

  def AddAnnotatedPerfStep(self, test_name, gtest_filter, log_type,
                           factory_properties, cmd_name='performance_ui_tests',
                           tool_opts=None, cmd_options=None, step_name=None):

    """Add an annotated perf step to the builder.

    Args:
      test_name: name of the test given to runtest.py. If step_name is not
        provided, a standard transform will be applied and the step on the
        waterfall will be test_name_test.

      gtest_filter: most steps use --gtest_filter to filter their output.

      log_type: one of the log parsers in runtest.py --annotate=list, such
        as 'graphing' or 'framerate'.

      cmd_name: command to run, by default 'performance_ui_tests'.

      tool_opts: additional options for runtest.py.

      cmd_options: additional options for the test run under runtest.py.

      step_name: the step name for the builder/waterfall.

      factory_properties: additional properties from the factory.
    """

    step_name = step_name or test_name.replace('-', '_') + '_test'
    factory_properties = factory_properties.copy()
    factory_properties['step_name'] = step_name

    cmd = self.GetAnnotatedPerfCmd(gtest_filter, log_type, test_name,
                                   cmd_name=cmd_name, options=cmd_options,
                                   tool_opts=tool_opts,
                                   factory_properties=factory_properties)

    self.AddTestStep(chromium_step.AnnotatedCommand, step_name, cmd,
                     do_step_if=self.TestStepFilter, target=self._target,
                     factory_properties=factory_properties)

  def AddCheckDepsStep(self):
    cmd = [self._python, self._check_deps_tool,
           '--root', self._repository_root]
    self.AddTestStep(shell.ShellCommand, 'check_deps', cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerCheckDepsStep(self):
    cmd = [self._python, self._check_deps_tool,
           '--root', self._repository_root]
    self.AddBuildrunnerTestStep(shell.ShellCommand, 'check_deps', cmd,
                                do_step_if=self.TestStepFilter)

  def AddCheckBinsStep(self):
    build_dir = os.path.join(self._build_dir, self._target)
    cmd = [self._python, self._check_bins_tool, build_dir]
    self.AddTestStep(shell.ShellCommand, 'check_bins', cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerCheckBinsStep(self):
    build_dir = os.path.join(self._build_dir, self._target)
    cmd = [self._python, self._check_bins_tool, build_dir]
    self.AddBuildrunnerTestStep(shell.ShellCommand, 'check_bins', cmd,
                                do_step_if=self.TestStepFilter)

  def AddCheckPermsStep(self):
    cmd = [self._python, self._check_perms_tool,
           '--root', self._repository_root]
    self.AddTestStep(shell.ShellCommand, 'check_perms', cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerCheckPermsStep(self):
    cmd = [self._python, self._check_perms_tool,
           '--root', self._repository_root]
    self.AddBuildrunnerTestStep(shell.ShellCommand, 'check_perms', cmd,
                                do_step_if=self.TestStepFilter)

  def AddCheckLicensesStep(self, factory_properties):
    cmd = [self._python, self._check_licenses_tool,
           '--root', self._repository_root]
    self.AddTestStep(shell.ShellCommand, 'check_licenses', cmd,
                     do_step_if=self.GetTestStepFilter(factory_properties))

  def AddBuildrunnerCheckLicensesStep(self, factory_properties):
    cmd = [self._python, self._check_licenses_tool,
           '--root', self._repository_root]
    self.AddBuildrunnerTestStep(shell.ShellCommand, 'check_licenses', cmd,
        do_step_if=self.GetTestStepFilter(factory_properties))

  def AddCheckLKGRStep(self):
    """Check LKGR; if unchanged, cancel the build.

    Unlike other "test step" commands, this one can cancel the build
    while still keeping it green.

    Note we use "." as a root (which is the same as self.working_dir)
    to make sure a clobber step deletes the saved lkgr file.
    """
    cmd = [self._python, self._check_lkgr_tool, '--root', '.']
    self.AddTestStep(commands.CanCancelBuildShellCommand,
                     'check lkgr and stop build if unchanged',
                     cmd)

  def AddMachPortsTests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('mach_ports', '--gtest_filter=MachPortsTest.*',
                              'graphing', step_name='mach_ports',
                              factory_properties=factory_properties)

  def GetPageCyclerCommand(self, test_name, http, factory_properties=None):
    """Returns a command list to call the _test_tool on the page_cycler
    executable, with the appropriate GTest filter and additional arguments.
    """
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]
    if http:
      test_type = 'Http'
      cmd.extend(['--with-httpd', self.PathJoin('src', 'data', 'page_cycler')])
    else:
      test_type = 'File'
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    cmd.extend([self.GetExecutableName('performance_ui_tests'),
                '--gtest_filter=PageCycler*.%s%s:PageCycler*.*_%s%s' % (
                    test_name, test_type, test_name, test_type)])
    return cmd

  def AddPageCyclerTest(self, test, factory_properties=None, suite=None):
    """Adds a step to the factory to run a page cycler test."""

    enable_http = test.endswith('-http')
    perf_dashboard_name = test.lstrip('page_cycler_')

    if suite:
      test_name = suite
    else:
      test_name = perf_dashboard_name.partition('-http')[0].capitalize()

    options = None
    if enable_http:
      test_type = 'Http'
      options = ['--with-httpd', self.PathJoin('src', 'data', 'page_cycler')]
    else:
      test_type = 'File'

    gtest_filter = 'PageCycler*.%s%s:PageCycler*.*_%s%s' % (
        test_name, test_type, test_name, test_type)

    self.AddAnnotatedPerfStep(perf_dashboard_name, gtest_filter, 'pagecycler',
                              tool_opts=options, step_name=test,
                              factory_properties=factory_properties)

  def AddStartupTests(self, factory_properties=None):
    test_list = 'StartupTest.*:ShutdownTest.*'
    # We don't need to run the Reference tests in debug mode.
    if self._target == 'Debug':
      test_list += ':-*.*Ref*'

    self.AddAnnotatedPerfStep('startup', test_list, 'graphing',
                              factory_properties=factory_properties)

  def AddMemoryTests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('memory', 'GeneralMix*MemoryTest.*', 'graphing',
                              factory_properties=factory_properties)

  def AddNewTabUITests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('new-tab-ui-cold', 'NewTabUIStartupTest.*Cold',
                              'graphing', factory_properties=factory_properties)
    self.AddAnnotatedPerfStep('new-tab-ui-warm', 'NewTabUIStartupTest.*Warm',
                              'graphing', factory_properties=factory_properties)

  def AddSyncPerfTests(self, factory_properties=None):
    options = ['--ui-test-action-max-timeout=120000']

    self.AddAnnotatedPerfStep('sync', '*SyncPerfTest.*', 'graphing',
                              cmd_options=options, step_name='sync',
                              factory_properties=factory_properties)

  def AddTabSwitchingTests(self, factory_properties=None):
    options = ['-enable-logging', '-dump-histograms-on-exit', '-log-level=0']

    self.AddAnnotatedPerfStep('tab-switching', 'TabSwitchingUITest.*',
                              'graphing', cmd_options=options,
                              factory_properties=factory_properties)

  def AddSizesTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'sizes',
                              process_log.GraphingLogProcessor)
    cmd = [self._python, self._sizes_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]
    # For Android, platform is hardcoded as target_platform is set to linux2.
    # By default, the sizes.py script looks at sys.platform to identify
    # the platform (which is also linux2).
    if self._target_os == 'android':
      cmd = cmd + ['--platform', 'android']

    self.AddTestStep(c, 'sizes', cmd,
                     do_step_if=self.TestStepFilter)

  def AddFrameRateTests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('frame_rate', 'FrameRate*Test*', 'framerate',
                              factory_properties=factory_properties)

  def AddGpuFrameRateTests(self, factory_properties=None):
    options = ['--enable-gpu']
    tool_options = ['--no-xvfb']

    self.AddAnnotatedPerfStep('gpu_frame_rate', 'FrameRate*Test*', 'framerate',
                              cmd_options=options, tool_opts=tool_options,
                              factory_properties=factory_properties)

  def AddGpuLatencyTests(self, factory_properties=None):
    options = ['--enable-gpu']
    tool_options = ['--no-xvfb']

    self.AddAnnotatedPerfStep('gpu_latency', 'LatencyTest*', 'graphing',
                              cmd_name='performance_browser_tests',
                              step_name='gpu_latency_tests',
                              cmd_options=options,
                              tool_opts=tool_options,
                              factory_properties=factory_properties)

  def AddGpuThroughputTests(self, factory_properties=None):
    options = ['--enable-gpu']
    tool_options = ['--no-xvfb']

    self.AddAnnotatedPerfStep('gpu_throughput', 'ThroughputTest*', 'graphing',
                              cmd_name='performance_browser_tests',
                              step_name='gpu_throughput_tests',
                              cmd_options=options,
                              tool_opts=tool_options,
                              factory_properties=factory_properties)

  def AddDomPerfTests(self, factory_properties):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'dom_perf',
                              process_log.GraphingLogProcessor)

    cmd = [self._python, self._dom_perf_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self.AddTestStep(c, 'dom_perf', cmd,
                     do_step_if=self.TestStepFilter)

  def AddIDBPerfTests(self, factory_properties):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'idb_perf',
                              process_log.GraphingLogProcessor)

    options = ['--gtest_filter=IndexedDBTest.Perf', '--gtest_print_time']
    cmd = self.GetTestCommand('performance_ui_tests', arg_list=options,
                              factory_properties=factory_properties)
    self.AddTestStep(c, 'idb_perf', cmd,
                     do_step_if=self.TestStepFilter)

  def AddChromeFramePerfTests(self, factory_properties):
    self.AddAnnotatedPerfStep('chrome_frame_perf', None, 'graphing',
                              cmd_name='chrome_frame_perftests',
                              step_name='chrome_frame_perf',
                              factory_properties=factory_properties)

  # Reliability sanity tests.
  def AddAnnotatedAutomatedUiTests(self, factory_properties=None):
    arg_list = ['--gtest_filter=-AutomatedUITest.TheOneAndOnlyTest']
    self.AddAnnotatedGTestTestStep('automated_ui_tests', factory_properties,
                                   arg_list=arg_list)

  def AddDeps2GitStep(self, verify=True):
    J = self.PathJoin
    deps2git_tool = J(self._repository_root, 'tools', 'deps2git', 'deps2git.py')
    cmd = [self._python, deps2git_tool,
           '-d', J(self._repository_root, 'DEPS'),
           '-o', J(self._repository_root, '.DEPS.git')]
    if verify:
      cmd.append('--verify')
    self.AddTestStep(
        shell.ShellCommand,
        'check_deps2git',
        cmd,
        do_step_if=self.TestStepFilter)

    deps2submodules_tool = J(self._repository_root, 'tools', 'deps2git',
                             'deps2submodules.py')
    cmd = [self._python, deps2submodules_tool, '--gitless',
           J(self._repository_root, '.DEPS.git')]
    self.AddTestStep(
        shell.ShellCommand,
        'check_deps2submodules',
        cmd,
        do_step_if=self.TestStepFilter)

  def AddBuildrunnerDeps2GitStep(self, verify=True):
    J = self.PathJoin
    deps2git_tool = J(self._repository_root, 'tools', 'deps2git', 'deps2git.py')
    cmd = [self._python, deps2git_tool,
           '-d', J(self._repository_root, 'DEPS'),
           '-o', J(self._repository_root, '.DEPS.git')]
    if verify:
      cmd.append('--verify')
    self.AddBuildrunnerTestStep(
        shell.ShellCommand,
        'check_deps2git',
        cmd,
        do_step_if=self.TestStepFilter)

    deps2submodules_tool = J(self._repository_root, 'tools', 'deps2git',
                             'deps2submodules.py')
    cmd = [self._python, deps2submodules_tool, '--gitless',
           J(self._repository_root, '.DEPS.git')]
    self.AddBuildrunnerTestStep(
        shell.ShellCommand,
        'check_deps2submodules',
        cmd,
        do_step_if=self.TestStepFilter)

  def AddReliabilityTests(self, platform):
    cmd = [self._python,
           self._reliability_tool,
           '--platform', platform,
           '--data-dir', self._reliability_data,
           '--build-id', WithProperties('%(build_id)s')]
    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     'reliability_tests', cmd)

  def AddAnnotatedInstallerTests(self, factory_properties):
    if self._target_platform == 'win32':
      self.AddAnnotatedGTestTestStep('installer_util_unittests',
                                     factory_properties)
      if (self._target == 'Release' and
          not factory_properties.get('disable_mini_installer_test')):
        self.AddAnnotatedGTestTestStep('mini_installer_test',
                                       factory_properties,
                                       arg_list=['-clean'])

  def AddBuildrunnerInstallerTests(self, factory_properties):
    if self._target_platform == 'win32':
      self.AddAnnotatedGTestTestStep('installer_util_unittests',
                                     factory_properties)
      if (self._target == 'Release' and
          not factory_properties.get('disable_mini_installer_test')):
        self.AddBuildrunnerGTest('mini_installer_test',
                                 factory_properties,
                                 arg_list=['-clean'])

  def AddAnnotatedChromeUnitTests(self, factory_properties):
    self.AddAnnotatedGTestTestStep('ipc_tests', factory_properties)
    self.AddAnnotatedGTestTestStep('sync_unit_tests', factory_properties)
    self.AddAnnotatedGTestTestStep('unit_tests', factory_properties)
    self.AddAnnotatedGTestTestStep('sql_unittests', factory_properties)
    self.AddAnnotatedGTestTestStep('ui_unittests', factory_properties)
    self.AddAnnotatedGTestTestStep('content_unittests', factory_properties)
    if self._target_platform == 'win32':
      self.AddAnnotatedGTestTestStep('views_unittests', factory_properties)

  def AddBuildrunnerChromeUnitTests(self, factory_properties):
    self.AddBuildrunnerGTest('ipc_tests', factory_properties)
    self.AddBuildrunnerGTest('sync_unit_tests', factory_properties)
    self.AddBuildrunnerGTest('unit_tests', factory_properties)
    self.AddBuildrunnerGTest('sql_unittests', factory_properties)
    self.AddBuildrunnerGTest('ui_unittests', factory_properties)
    self.AddBuildrunnerGTest('content_unittests', factory_properties)
    if self._target_platform == 'win32':
      self.AddBuildrunnerGTest('views_unittests', factory_properties)

  def AddAnnotatedSyncIntegrationTests(self, factory_properties):
    options = ['--ui-test-action-max-timeout=120000']

    self.AddAnnotatedGTestTestStep('sync_integration_tests',
                                   factory_properties, '',
                                   options)

  def AddBuildrunnerSyncIntegrationTests(self, factory_properties):
    options = ['--ui-test-action-max-timeout=120000']

    self.AddBuildrunnerGTest('sync_integration_tests',
                             factory_properties, '',
                             options)

  def AddAnnotatedBrowserTests(self, factory_properties=None):
    description = ''
    options = ['--lib=browser_tests']

    total_shards = factory_properties.get('browser_total_shards')
    shard_index = factory_properties.get('browser_shard_index')
    options.append(factory_properties.get('browser_tests_filter', []))

    options = filter(None, options)

    self.AddAnnotatedGTestTestStep('browser_tests', factory_properties,
                                   description, options,
                                   total_shards=total_shards,
                                   shard_index=shard_index)

  def AddBuildrunnerBrowserTests(self, factory_properties):
    description = ''
    options = ['--lib=browser_tests']

    total_shards = factory_properties.get('browser_total_shards')
    shard_index = factory_properties.get('browser_shard_index')
    options.append(factory_properties.get('browser_tests_filter', []))

    options = filter(None, options)

    self.AddBuildrunnerGTest('browser_tests', factory_properties,
                             description, options,
                             total_shards=total_shards,
                             shard_index=shard_index)

  def AddDomCheckerTests(self):
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    cmd.extend(['--with-httpd',
                self.PathJoin('src', 'chrome', 'test', 'data')])

    cmd.extend([self.GetExecutableName('performance_ui_tests'),
                '--gtest_filter=DomCheckerTest.*',
                '--gtest_print_time',
                '--run-dom-checker-test'])

    self.AddTestStep(shell.ShellCommand, 'dom_checker_tests', cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerDomCheckerTests(self):
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    cmd.extend(['--with-httpd',
                self.PathJoin('src', 'chrome', 'test', 'data')])

    cmd.extend([self.GetExecutableName('performance_ui_tests'),
                '--gtest_filter=DomCheckerTest.*',
                '--gtest_print_time',
                '--run-dom-checker-test'])

    self.AddBuildrunnerTestStep(shell.ShellCommand, 'dom_checker_tests', cmd,
                                do_step_if=self.TestStepFilter)

  def AddMemoryTest(self, test_name, tool_name, timeout=1200,
                    factory_properties=None,
                    command_class=gtest_command.GTestFullCommand,
                    wrapper_args=None):
    factory_properties = factory_properties or {}
    # TODO(timurrrr): merge this with Heapcheck runner. http://crbug.com/45482
    build_dir = os.path.join(self._build_dir, self._target)
    if self._target_platform == 'darwin':  # Mac bins reside in src/xcodebuild
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'xcodebuild',
                               self._target)
    elif self._target_platform == 'linux2':  # Linux bins in src/sconsbuild
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'sconsbuild',
                               self._target)
    elif self._target_platform == 'win32':  # Windows binaries are in src/build
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'build',
                               self._target)
    if not wrapper_args:
      wrapper_args = []
    do_step_if = self.TestStepFilter
    matched = re.search(r'_([0-9]*)_of_([0-9]*)$', test_name)
    if matched:
      test_name = test_name[0:matched.start()]
      shard = int(matched.group(1))
      numshards = int(matched.group(2))
      wrapper_args.extend(['--shard-index', str(shard),
                           '--total-shards', str(numshards)])
      if test_name in factory_properties.get('sharded_tests', []):
        wrapper_args.append('--parallel')
        sharding_args = factory_properties.get('sharding_args')
        if sharding_args:
          wrapper_args.extend(['--sharding-args', sharding_args])
    elif test_name.endswith('_gtest_filter_required'):
      test_name = test_name[0:-len('_gtest_filter_required')]
      do_step_if = self.TestStepFilterGTestFilterRequired

    # Memory tests runner script path is relative to build_dir.
    if self._target_platform != 'win32':
      runner = os.path.join('..', '..', '..', self._posix_memory_tests_runner)
    else:
      runner = os.path.join('..', '..', '..', self._win_memory_tests_runner)

    cmd = self.GetShellTestCommand(runner, arg_list=[
        '--build_dir', build_dir,
        '--test', test_name,
        '--tool', tool_name,
        WithProperties('%(gtest_filter)s')],
        wrapper_args=wrapper_args,
        factory_properties=factory_properties)

    test_name = 'memory test: %s' % test_name
    self.AddTestStep(command_class, test_name, cmd,
                     timeout=timeout,
                     do_step_if=do_step_if)

  def AddAnnotatedMemoryTest(self, test_name, tool_name, timeout=1200,
                    factory_properties=None):
    factory_properties = factory_properties or {}
    factory_properties['full_test_name'] = True
    self.AddMemoryTest(test_name, tool_name, timeout, factory_properties,
                       wrapper_args=[
                           '--annotate=gtest',
                           '--test-type', 'memory test: %s' % test_name
                       ],
                       command_class=chromium_step.AnnotatedCommand)

  def AddHeapcheckTest(self, test_name, timeout, factory_properties,
                       command_class=gtest_command.GTestFullCommand,
                       wrapper_args=None):
    build_dir = os.path.join(self._build_dir, self._target)
    if self._target_platform == 'linux2':  # Linux bins in src/sconsbuild
      build_dir = os.path.join(os.path.dirname(self._build_dir), 'sconsbuild',
                               self._target)

    wrapper_args = wrapper_args or []

    matched = re.search(r'_([0-9]*)_of_([0-9]*)$', test_name)
    if matched:
      test_name = test_name[0:matched.start()]
      shard = int(matched.group(1))
      numshards = int(matched.group(2))
      wrapper_args.extend(['--shard-index', str(shard),
                           '--total-shards', str(numshards)])

    heapcheck_tool = os.path.join('..', '..', '..', self._heapcheck_tool)

    cmd = self.GetShellTestCommand(heapcheck_tool, arg_list=[
        '--build_dir', build_dir,
        '--test', test_name],
        wrapper_args=wrapper_args,
        factory_properties=factory_properties)

    test_name = 'heapcheck test: %s' % test_name
    self.AddTestStep(command_class, test_name, cmd,
                     timeout=timeout,
                     do_step_if=self.TestStepFilter)

  def AddAnnotatedHeapcheckTest(self, test_name, timeout, factory_properties):
    factory_properties = factory_properties or {}
    factory_properties['full_test_name'] = True
    self.AddHeapcheckTest(test_name, timeout, factory_properties,
                          wrapper_args=[
                              '--annotate=gtest',
                              '--test-type', 'heapcheck test: %s' % test_name
                          ],
                          command_class=chromium_step.AnnotatedCommand)

  def _AddBasicPythonTest(self, test_name, script, args=None, timeout=1200):
    args = args or []
    J = self.PathJoin
    if self._target_platform == 'win32':
      py26 = J('src', 'third_party', 'python_26', 'python_slave.exe')
      test_cmd = ['cmd', '/C'] + [py26, script] + args
    elif self._target_platform == 'darwin':
      test_cmd = ['python2.6', script] + args
    elif self._target_platform == 'linux2':
      # Run thru runtest.py on linux to launch virtual x server
      test_cmd = self.GetTestCommand('/usr/local/bin/python2.6',
                                     [script] + args)

    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     test_name,
                     test_cmd,
                     timeout=timeout,
                     do_step_if=self.TestStepFilter)

  def AddChromeDriverTest(self, timeout=1200):
    J = self.PathJoin
    script = J('src', 'chrome', 'test', 'webdriver', 'test',
               'run_chromedriver_tests.py')
    self._AddBasicPythonTest('chromedriver_tests', script, timeout=timeout)

  def AddWebDriverTest(self, timeout=1200):
    J = self.PathJoin
    script = J('src', 'chrome', 'test', 'webdriver', 'test',
               'run_webdriver_tests.py')
    self._AddBasicPythonTest('webdriver_tests', script, timeout=timeout)

  def _GetReferenceBuildPath(self):
    J = self.PathJoin
    ref_dir = J('src', 'chrome', 'tools', 'test', 'reference_build')
    if self._target_os == 'android':
      # TODO(tonyg): Check in a reference android content shell.
      return None
    elif self._target_platform == 'win32':
      return J(ref_dir, 'chrome_win', 'chrome.exe')
    elif self._target_platform == 'darwin':
      return J(ref_dir, 'chrome_mac', 'Chromium.app', 'Contents', 'MacOS',
               'Chromium')
    elif self._target_platform.startswith('linux'):
      return J(ref_dir, 'chrome_linux', 'chrome')
    return None

  def AddTelemetryTest(self, test_name, page_set, step_name=None,
                       factory_properties=None, timeout=1200):
    """Adds a Telemetry performance test.

    TODO(tonyg): Move this to an annotator step once we have a annotation for
    the GraphingLogProcessor.

    Args:
      test_name: The name of the benchmark module to run.
      page_set: The path to the page set to run the benchmark against. Must be
          relative to src/tools/perf/page_sets/.
      step_name: The name used to build the step's logfile name and descriptions
          in the waterfall display. Defaults to |test_name|.
      factory_properties: A dictionary of factory property values.
    """
    step_name = step_name or test_name
    factory_properties = factory_properties or {}
    J = self.PathJoin

    script = J('src', 'tools', 'perf', 'run_multipage_benchmarks')
    page_set = J('src', 'tools', 'perf', 'page_sets', page_set)

    # Run the test against the target chrome build.
    browser = 'release'
    if self._target_os == 'android':
      browser = 'android-content-shell'
    test_args = ['-v', '--browser=%s' % browser, test_name, page_set]
    test_cmd = self.GetPythonTestCommand(script, test_args)
    cmd = ' '.join(test_cmd)

    # Run the test against the reference build on platforms where it exists.
    ref_build = self._GetReferenceBuildPath()
    if ref_build:
      ref_args = ['-v', '--browser=exact',
                  '--browser-executable=%s' % ref_build,
                  test_name, page_set]
      ref_cmd = self.GetPythonTestCommand(script, ref_args)
      cmd += ' && ' + ' '.join(ref_cmd)

    # On android, telemetry needs to use the adb command and needs to be in
    # root mode. Run it in bash since envsetup.sh doesn't work in sh.
    if self._target_os == 'android':
      cmd = ('bash -c ". src/build/android/envsetup.sh && ' +
             'adb root && adb wait-for-device && %s"' % cmd)

    command_class = self.GetPerfStepClass(
        factory_properties, step_name, process_log.GraphingLogProcessor)
    self.AddTestStep(command_class, step_name, cmd, timeout=timeout,
                     do_step_if=self.TestStepFilter)

  def AddPyAutoFunctionalTest(self, test_name, timeout=1200,
                              workdir=None,
                              src_base='.',
                              suite=None,
                              test_args=None,
                              factory_properties=None,
                              perf=False):
    """Adds a step to run PyAuto functional tests.

    Args:
      test_name: a string describing the test, used to build its logfile name
          and its descriptions in the waterfall display
      timeout: The buildbot timeout for this step, in seconds.  The step will
          fail if the test does not produce any output within this time.
      workdir: the working dir for this step
      src_base: relative path (from workdir) to src. Not needed if workdir is
          'build' (the default)
      suite: PyAuto suite to execute.
      test_args: list of PyAuto test arguments.
      factory_properties: A dictionary of factory property values.
      perf: Is this a perf test or not? Requires suite or test_args to be set.
    """
    factory_properties = factory_properties or {}
    J = self.PathJoin
    pyauto_script = J(src_base, 'src', 'chrome', 'test', 'functional',
                      'pyauto_functional.py')
    pyauto_cmd = ['python', pyauto_script, '-v']
    if self._target_platform == 'win32':
      pyauto_cmd = self.GetPythonTestCommand(pyauto_script, ['-v'])
      pyauto_cmd[1] = J(src_base, pyauto_cmd[1])  # adjust runtest.py if needed
    elif self._target_platform == 'darwin':
      pyauto_cmd = self.GetTestCommand('/usr/bin/python2.5',
                                       [pyauto_script, '-v'])
      pyauto_cmd[1] = J(src_base, pyauto_cmd[1])  # adjust runtest.py if needed
    elif (self._target_platform.startswith('linux') and
          factory_properties.get('use_xvfb_on_linux')):
      # On Linux, use runtest.py to launch virtual X server.
      pyauto_cmd = self.GetTestCommand('/usr/bin/python', [pyauto_script, '-v'])
      pyauto_cmd[1] = J(src_base, pyauto_cmd[1])  # adjust runtest.py if needed

    if suite:
      pyauto_cmd.append('--suite=%s' % suite)
    if test_args:
      pyauto_cmd.extend(test_args)

    command_class = retcode_command.ReturnCodeCommand
    if perf and (suite or test_args):
      # Use special command class for parsing perf values from output.
      command_class = self.GetPerfStepClass(
          factory_properties, test_name, process_log.GraphingLogProcessor)

    self.AddTestStep(command_class,
                     test_name,
                     pyauto_cmd,
                     env={'PYTHONPATH': '.'},
                     workdir=workdir,
                     timeout=timeout,
                     do_step_if=self.GetTestStepFilter(factory_properties))

  def AddChromeEndureTest(self, test_class_name, pyauto_test_list,
                          factory_properties, timeout=1200, wpr=False):
    """Adds a step to run PyAuto-based Chrome Endure tests.

    Args:
      test_class_name: A string name for this class of tests.
      pyauto_test_list: A list of strings, where each string is the full name
          of a pyauto test to run (file.class.test_name).
      factory_properties: A dictionary of factory property values.
      timeout: The buildbot timeout for this step, in seconds.  The step will
          fail if the test does not produce any output within this time.
      wpr: A boolean indicating whether or not to run the test using Web Page
          replay (WPR).  If using WPR, the test will replay webapp interactions
          from a pre-recorded file, rather than using the live site.
    """
    pyauto_script = self.PathJoin('src', 'chrome', 'test', 'functional',
                                  'pyauto_functional.py')
    # Only run on linux for now.
    if not self._target_platform.startswith('linux'):
      return

    env = factory_properties.get('test_env', {})
    if 'PYTHONPATH' not in env:
      env['PYTHONPATH'] = '.'
    if not wpr:
      env['ENDURE_NO_WPR'] = '1'

    for pyauto_test_name in pyauto_test_list:
      pyauto_cmd = ['python', pyauto_script, '-v']
      if factory_properties.get('use_xvfb_on_linux'):
        # Run through runtest.py on linux to launch virtual x server.
        pyauto_cmd = self.GetTestCommand('/usr/bin/python',
                                         [pyauto_script, '-v'])
      pyauto_cmd.append(pyauto_test_name)
      test_step_name = (test_class_name + ' ' +
                        pyauto_test_name[pyauto_test_name.rfind('.') + 1:])
      self.AddTestStep(retcode_command.ReturnCodeCommand,
                       test_step_name,
                       pyauto_cmd,
                       env=env,
                       timeout=timeout,
                       do_step_if=self.GetTestStepFilter(factory_properties))

  def AddDevToolsTests(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'devtools_perf',
                              process_log.GraphingLogProcessor)

    cmd = [self._python, self._devtools_perf_test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir
    ]
    self.AddTestStep(c,
                     test_name='DevTools.PerfTest',
                     test_command=cmd,
                     do_step_if=self.TestStepFilter)

    def AddFunctionalTest(test_name, script_name):
      pyauto_script = self.PathJoin('src', 'chrome', 'test', 'functional',
                                    script_name)
      # Run through runtest.py to launch virtual x server.
      cmd = self.GetTestCommand('/usr/bin/python', [pyauto_script])
      self.AddTestStep(c, test_name, cmd, do_step_if=self.TestStepFilter)

    AddFunctionalTest('DevTools.NativeSnapshotUnknownSize',
                      'devtools_native_memory_snapshot.py')
    if self._target == 'Release':
      AddFunctionalTest('DevTools.CheckMemoryInstrumentation',
                        'devtools_instrumented_objects_check.py')

  def AddWebkitLint(self, factory_properties=None):
    """Adds a step to the factory to lint the test_expectations.txt file."""
    cmd = [self._python, self._lint_test_files_tool,
           '--build-dir', self._build_dir, '--target', self._target]
    self.AddTestStep(shell.ShellCommand,
                     test_name='webkit_lint',
                     test_command=cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerWebkitLint(self, factory_properties=None):
    """Adds a step to the factory to lint the test_expectations.txt file."""
    cmd = [self._python, self._lint_test_files_tool,
           '--build-dir', self._build_dir, '--target', self._target]
    self.AddBuildrunnerTestStep(shell.ShellCommand,
                                test_name='webkit_lint',
                                test_command=cmd,
                                do_step_if=self.TestStepFilter)

  def AddWebkitTests(self, factory_properties=None):
    """Adds a step to the factory to run the WebKit layout tests.

    Args:
      with_pageheap: if True, page-heap checking will be enabled for test_shell
      test_timeout: buildbot timeout for the test step
      archive_timeout: buildbot timeout for archiving the test results and
          crashes, if requested
      archive_results: whether to archive the test results
      archive_crashes: whether to archive crash reports resulting from the
          tests
      test_results_server: If specified, upload results json files to test
          results server
      driver_name: If specified, alternate layout test driver to use.
      additional_drt_flag: If specified, additional flag to pass to DRT.
      layout_tests: List of layout tests to run.
    """
    factory_properties = factory_properties or {}
    with_pageheap = factory_properties.get('webkit_pageheap')
    archive_results = factory_properties.get('archive_webkit_results')
    layout_part = factory_properties.get('layout_part')
    test_results_server = factory_properties.get('test_results_server')
    platform = factory_properties.get('layout_test_platform')
    enable_hardware_gpu = factory_properties.get('enable_hardware_gpu')
    layout_tests = factory_properties.get('layout_tests')
    time_out_ms = factory_properties.get('time_out_ms')
    driver_name = factory_properties.get('driver_name')
    additional_drt_flag = factory_properties.get('additional_drt_flag')

    builder_name = '%(buildername)s'
    result_str = 'results'
    test_name = 'webkit_tests'

    pageheap_description = ''
    if with_pageheap:
      pageheap_description = ' (--enable-pageheap)'

    webkit_result_dir = '/'.join(['..', '..', 'layout-test-results'])

    cmd_args = ['--target', self._target,
                '-o', webkit_result_dir,
                '--build-dir', self._build_dir,
                '--build-number', WithProperties('%(buildnumber)s'),
                '--builder-name', WithProperties(builder_name)]

    for comps in factory_properties.get('additional_expectations_files', []):
      cmd_args.append('--additional-expectations-file')
      cmd_args.append(self.PathJoin('src', *comps))

    if layout_part:
      cmd_args.extend(['--run-part', layout_part])

    if with_pageheap:
      cmd_args.append('--enable-pageheap')

    if test_results_server:
      cmd_args.extend(['--test-results-server', test_results_server])
    if platform:
      cmd_args.extend(['--platform', platform])

    if enable_hardware_gpu:
      cmd_args.extend(['--options=--enable-hardware-gpu'])

    if time_out_ms:
      cmd_args.extend(['--time-out-ms', time_out_ms])

    if driver_name:
      cmd_args.extend(['--driver-name', driver_name])

    if additional_drt_flag:
      cmd_args.extend(['--additional-drt-flag', additional_drt_flag])

    # The list of tests is given as arguments.
    if layout_tests:
      cmd_args.extend(layout_tests)

    cmd = self.GetPythonTestCommand(self._layout_test_tool,
                                    cmd_args,
                                    wrapper_args=['--no-xvfb'])

    self.AddTestStep(webkit_test_command.WebKitCommand,
                     test_name=test_name,
                     test_description=pageheap_description,
                     test_command=cmd,
                     do_step_if=self.TestStepFilter)

    if archive_results:
      cmd = [self._python, self._layout_archive_tool,
             '--results-dir', webkit_result_dir,
             '--build-dir', self._build_dir,
             '--build-number', WithProperties('%(buildnumber)s'),
             '--builder-name', WithProperties(builder_name)]

      cmd = self.AddBuildProperties(cmd)
      cmd = self.AddFactoryProperties(factory_properties, cmd)

      self.AddArchiveStep(
          data_description='webkit_tests ' + result_str,
          base_url=_GetArchiveUrl('layout_test_results'),
          link_text='layout test ' + result_str,
          command=cmd)

  def AddWebRTCTests(self, tests, factory_properties, test_timeout=1200):
    """Adds a list of tests, possibly prefixed for running within a tool.

    To run a test under memcheck, prefix the test name with 'memcheck_'.
    To run a test under tsan, prefix the test name with 'tsan_'.

    Args:
      tests: List of test names, possibly prefixed as described above.
      factory_properties: Dict of properties to be used during execution.
      test_timeout: Max time a test may run before it is killed.
    """
    for test in tests:
      if test.startswith('memcheck_'):
        self.AddMemoryTest(test[len('memcheck_'):], 'memcheck', test_timeout,
                           factory_properties)
      elif test.startswith('tsan_'):
        self.AddMemoryTest(test[len('tsan_'):], 'tsan', test_timeout,
                           factory_properties)
      else:
        self.AddAnnotatedGTestTestStep(test, factory_properties)

  def AddRunCrashHandler(self, build_dir=None, target=None):
    build_dir = build_dir or self._build_dir
    target = target or self._target
    cmd = [self._python, self._crash_handler_tool,
           '--build-dir', build_dir,
           '--target', target]
    self.AddTestStep(shell.ShellCommand, 'start_crash_handler', cmd)

  def AddProcessDumps(self):
    cmd = [self._python, self._process_dumps_tool,
           '--build-dir', self._build_dir,
           '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'process_dumps', cmd)

  def AddRunCoverageBundles(self, factory_properties=None):
    # If updating this command, update the mirror of it in chrome_tests.gypi.
    cmd = [self._python,
           os.path.join('src', 'tools', 'code_coverage', 'coverage_posix.py'),
           '--build-dir',
           self._build_dir,
           '--target',
           self._target,
           '--src_root',
           '.',
           '--bundles', 'coverage_bundles.py']
    self.AddTestStep(shell.ShellCommand, 'run_coverage_bundles', cmd)
    # Run only unittests in this step.
    cmd = [self._python,
           os.path.join('src', 'tools', 'code_coverage', 'coverage_posix.py'),
           '--build-dir',
           self._build_dir,
           '--target',
           self._target,
           '--src_root',
           '.',
           '--all_unittests', 'True']
    self.AddTestStep(shell.ShellCommand, 'run_unittests_only', cmd)

  def AddProcessCoverage(self, factory_properties=None):
    factory_properties = factory_properties or {}
    c = self.GetPerfStepClass(factory_properties, 'coverage',
                              process_log.GraphingLogProcessor)

    cmd = [self._python, self._process_coverage_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    self.AddTestStep(c, 'process_coverage', cmd)

    # Map the perf ID to the coverage subdir, so we can link from the coverage
    # graph
    perf_mapping = self.PERF_TEST_MAPPINGS[self._target]
    perf_id = factory_properties.get('perf_id')
    perf_subdir = perf_mapping.get(perf_id)

    url = _GetArchiveUrl('coverage', perf_subdir)
    text = 'view coverage'
    cmd_archive = [self._python, self._archive_coverage,
                   '--target', self._target,
                   '--build-dir', self._build_dir,
                   '--perf-subdir', perf_subdir]
    if factory_properties.get('use_build_number'):
      cmd_archive.extend(['--build-number', WithProperties('%(buildnumber)s')])

    self.AddArchiveStep(data_description='coverage', base_url=url,
                        link_text=text, command=cmd_archive)

  def AddSendTestParityStep(self, platform):
    cmd = [self._python,
           self._upload_parity_tool,
           self._build_dir,
           'http://chrome-test-parity.appspot.com/bulk_update',
           platform]
    self.AddTestStep(shell.ShellCommand, 'upload test parity', cmd)

  def AddDownloadAndExtractOfficialBuild(self, qa_identifier, branch=None):
    """Download and extract an official build.

    Assumes the zip file has e.g. "Google Chrome.app" in the top level
    directory of the zip file.
    """
    cmd = [self._python, self._download_and_extract_official_tool,
           '--identifier', qa_identifier,
           # TODO(jrg): for now we are triggered on a timer and always
           # use the latest build.  Instead we should trigger on the
           # presence of new build and pass that info down for a
           # --build N arg.
           '--latest']
    if branch:  # Fetch latest on given branch
      cmd += ['--branch', str(branch)]
    self.AddTestStep(commands.WaterfallLoggingShellCommand,
                     'Download and extract official build', cmd,
                     halt_on_failure=True)

  def AddAnnotatedSoftGpuTests(self, factory_properties):
    """Runs gpu_tests with software rendering and archives any results.
    """
    tests = ':'.join(['GpuPixelBrowserTest.*', 'GpuFeatureTest.*',
                      'Canvas2DPixelTestSD.*', 'Canvas2DPixelTestHD.*'])
    # 'GPUCrashTest.*', while interesting, fails.

    # TODO(petermayo): Invoke the new executable when it is ready.
    self.AddAnnotatedGTestTestStep('gpu_tests', factory_properties,
                                   description='(soft)',
                                   arg_list=['--gtest_also_run_disabled_tests',
                                             '--gtest_filter=%s' % tests],
                                   test_tool_arg_list=['--llvmpipe'])

    # Note: we aren't archiving these for the moment.

  def AddAnnotatedGpuTests(self, factory_properties):
    """Runs gpu_tests binary and archives any results.

    This binary contains browser tests that should be run on the gpu bots.
    """
    # Put gpu data in /b/build/slave/SLAVE_NAME/gpu_data
    gpu_data = self.PathJoin('..', 'gpu_data')
    gen_dir = self.PathJoin(gpu_data, 'generated')
    ref_dir = self.PathJoin(gpu_data, 'reference')

    self.AddAnnotatedGTestTestStep('gpu_tests', factory_properties,
                                   arg_list=['--use-gpu-in-tests',
                                             '--generated-dir=%s' % gen_dir,
                                             '--reference-dir=%s' % ref_dir],
                                   test_tool_arg_list=['--no-xvfb'])

    # Setup environment for running gsutil, a Google Storage utility.
    gsutil = 'gsutil'
    if self._target_platform.startswith('win'):
      gsutil = 'gsutil.bat'
    env = {}
    env['GSUTIL'] = self.PathJoin(self._script_dir, gsutil)

    cmd = [self._python,
           self._gpu_archive_tool,
           '--run-id', WithProperties('%(got_revision)s_%(buildername)s'),
           '--generated-dir', gen_dir,
           '--gpu-reference-dir', ref_dir]
    self.AddTestStep(shell.ShellCommand, 'archive test results', cmd, env=env)

  def AddAnnotatedGpuContentTests(self, factory_properties):
    """Runs content_browsertests binary with selected gpu tests.

    This binary contains content side browser tests that should be run on the
    gpu bots.
    """
    tests = ':'.join(['WebGLConformanceTest.*', 'GpuCrashTest.*'])

    self.AddAnnotatedGTestTestStep('content_browsertests', factory_properties,
                                   arg_list=['--use-gpu-in-tests',
                                             '--gtest_filter=%s' % tests,
                                             '--run-manual'],
                                   test_tool_arg_list=['--no-xvfb'])

  def AddAnnotatedGLTests(self, factory_properties=None):
    """Runs gl_tests binary.

    This binary contains unit tests that should be run on the gpu bots.
    """
    factory_properties = factory_properties or {}

    self.AddAnnotatedGTestTestStep('gl_tests', factory_properties,
                                   test_tool_arg_list=['--no-xvfb'])

  def AddAnnotatedGLES2ConformTest(self, factory_properties=None):
    """Runs gles2_conform_test binary.

    This binary contains the OpenGL ES 2.0 Conformance tests to be run on the
    gpu bots.
    """
    factory_properties = factory_properties or {}

    self.AddAnnotatedGTestTestStep('gles2_conform_test', factory_properties,
                                   test_tool_arg_list=['--no-xvfb'])

  def AddNaClIntegrationTestStep(self, factory_properties, target=None,
                                 buildbot_preset=None, timeout=1200):
    target = target or self._target
    cmd = [self._python, self._nacl_integration_tester_tool,
           '--mode', target]
    if buildbot_preset is not None:
      cmd.extend(['--buildbot', buildbot_preset])

    self.AddTestStep(chromium_step.AnnotatedCommand, 'nacl_integration', cmd,
                     halt_on_failure=True, timeout=timeout,
                     do_step_if=self.TestStepFilter)

  def AddAnnotatedSteps(self, factory_properties, timeout=1200):
    factory_properties = factory_properties or {}
    script = self.PathJoin(self._chromium_script_dir,
                           factory_properties.get('annotated_script', ''))
    cmd = [self._python, script]
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotated_steps',
                          description='annotated_steps',
                          timeout=timeout,
                          haltOnFailure=True,
                          command=cmd)

  def AddAnnotationStep(self, name, cmd, factory_properties=None, env=None,
                        timeout=6000):
    """Add an @@@BUILD_STEP step@@@ annotation script build command.

    This function allows the caller to specify the name of the
    annotation script.  In contrast, AddAnnotatedSteps() simply adds
    in a hard-coded annotation script that is not yet in the tree.
    TODO(jrg): resolve this inconsistency with the
    chrome-infrastrucure team; we shouldn't need two functions.
    """
    factory_properties = factory_properties or {}

    # Ensure cmd is a list, which is required for AddBuildProperties.
    if not isinstance(cmd, list):
      cmd = [cmd]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name=name,
                          description=name,
                          timeout=timeout,
                          haltOnFailure=True,
                          command=cmd,
                          env=env,
                          factory_properties=factory_properties)

  def AddMediaTests(self, test_groups, factory_properties=None, timeout=1200):
    """Adds media test steps according to the specified test_groups.

    Args:
      test_groups: List of (str:Name, bool:Perf?) tuples which should be
        translated into test steps.
    """
    for group, is_perf in test_groups:
      self.AddPyAutoFunctionalTest(
          'media_tests_' + group.lower(), suite=group, timeout=timeout,
          perf=is_perf, factory_properties=factory_properties)

  def AddChromebotServer(self, factory_properties=None):
    """Add steps to run Chromebot script for server.

    This expects build property to be set with Chromium build number, which
    is set by SetBuildPropertyShellCommand in GetBuildForChromebot step.

    Args:
      client_os: Target client OS (win or linux).
      server_port: Port for client/server communication.
      timeout: Max time (secs) to run Chromebot server script.
      build_type: Either 'official' or 'chromium'.
      build_id: ID of the extracted Chrome build.
    """
    factory_properties = factory_properties or {}
    client_os = factory_properties.get('client_os')
    server_port = factory_properties.get('server_port')
    timeout = factory_properties.get('timeout')
    build_type = factory_properties.get('build_type')
    max_time = timeout + 5 * 60  # Increase timeout by 5 minutes.
    build_id = WithProperties('%(build_id)s')

    # Chromebot script paths.
    chromebot_path = self.PathJoin('src', 'tools', 'chromebot')
    chromebot_script = self.PathJoin(chromebot_path, 'chromebot.py')
    url_file = self.PathJoin(chromebot_path, 'top-million')

    # Add trigger step.
    self._factory.addStep(trigger.Trigger(
        schedulerNames=[factory_properties.get('trigger')],
        updateSourceStamp=False,
        waitForFinish=False))

    # Add step to run Chromebot server script.
    cmd = [self._python,
           chromebot_script,
           url_file,
           '--build-id', build_id,
           '--build-type', build_type,
           '--client-os', client_os,
           '--log-level', 'INFO',
           '--timeout', str(timeout),
           '--mode', 'server',
           '--server-port', str(server_port)]
    self.AddTestStep(shell.ShellCommand, 'run_chromebot_server', cmd,
                     max_time=max_time, do_step_if=self.TestStepFilter)

  def AddChromebotClient(self, factory_properties=None):
    """Add steps to run Chromebot script for server and client side.

    This expects build property to be set with Chromium build number, which
    is set by SetBuildPropertyShellCommand in GetBuildForChromebot step.

    Args:
      client_os: Target client OS (win or linux).
      server_hostname: Hostname of Chromebot server machine.
      server_port: Port for client/server communication.
      build_id: ID of the extracted Chrome build.
    """
    factory_properties = factory_properties or {}
    client_os = factory_properties.get('client_os')
    server_hostname = factory_properties.get('server_hostname')
    server_port = factory_properties.get('server_port')
    proxy_servers = factory_properties.get('proxy_servers')
    timeout = factory_properties.get('timeout')
    max_time = timeout + 5 * 60  # Increase timeout by 5 minutes.
    build_id = WithProperties('%(build_id)s')

    # Chromebot script paths.
    chromebot_path = self.PathJoin('src', 'tools', 'chromebot')
    chromebot_script = self.PathJoin(chromebot_path, 'chromebot.py')
    symbol_path = self.PathJoin(self._build_dir, 'breakpad_syms')
    target_path = self.PathJoin(self._build_dir, self._target)

    # Add step to run Chromebot client script.
    cmd = [self._python,
           chromebot_script,
           '--build-dir', target_path,
           '--build-id', build_id,
           '--client-os', client_os,
           '--log-level', 'INFO',
           '--mode', 'client',
           '--server', server_hostname,
           '--server-port', str(server_port),
           '--proxy-servers', ','.join(proxy_servers),
           '--symbols-dir', symbol_path]
    self.AddTestStep(shell.ShellCommand, 'run_chromebot_client', cmd,
                     max_time=max_time, do_step_if=self.TestStepFilter)

  # TODO(csharp): Move this function into commands once swarm test can be added
  # via AddTestStep.
  def AddTriggerSwarmTests(self, tests, factory_properties):
    """Generate the hash for each swarm result file and then trigger the swarm
    tests."""
    using_ninja = (
        'ninja' in factory_properties['gclient_env'].get('GYP_GENERATORS', ''))

    # TODO(csharp): Actually send the tests instead of just an empty list
    # once all tests have result files.
    self.AddGenerateResultHashesStep(
        using_ninja, [], doStepIf=swarm_commands.TestStepFilterSwarm)

    # Trigger the swarm test builder.
    properties = {
        'issue': WithProperties('%(issue:-)s'),
        'target_os': self._target_platform,
        'parent_buildername': WithProperties('%(buildername:-)s'),
        'parent_buildnumber': WithProperties('%(buildnumber:-)s'),
        'parent_try_job_key': WithProperties('%(try_job_key:-)s'),
        'patchset': WithProperties('%(patchset:-)s')
    }
    self._factory.addStep(
        trigger.Trigger(
            name='trigger_swarm_triggered',
            schedulerNames=['swarm_triggered'],
            updateSourceStamp=False,
            waitForFinish=False,
            set_properties=properties,
            copy_properties=['swarm_hashes', 'testfilter'],
            doStepIf=swarm_commands.TestStepFilterSwarm))


def _GetArchiveUrl(archive_type, builder_name='%(build_name)s'):
  # The default builder name is dynamically filled in by
  # ArchiveCommand.createSummary.
  return '%s/%s/%s' % (config.Master.archive_url, archive_type, builder_name)


def _GetSnapshotUrl(factory_properties=None, builder_name='%(build_name)s'):
  if not factory_properties or 'gs_bucket' not in factory_properties:
    return (_GetArchiveUrl('snapshots', builder_name), None)
  gs_bucket = factory_properties['gs_bucket']
  gs_bucket = re.sub(r'^gs://', 'http://commondatastorage.googleapis.com/',
                     gs_bucket)
  return ('%s/index.html?path=%s' % (gs_bucket, builder_name), '/')
