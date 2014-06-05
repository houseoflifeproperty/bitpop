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
    self._bb_dir = self.PathJoin('src', 'build', 'android', 'buildbot')

    # Create smaller name for the functions and vars to simplify the code below.
    J = self.PathJoin
    s_dir = self._chromium_script_dir
    p_dir = self._private_script_dir

    self._process_dumps_tool = self.PathJoin(self._script_dir,
                                             'process_dumps.py')
    gsutil = 'gsutil'
    if self._target_platform and self._target_platform.startswith('win'):
      gsutil = 'gsutil.bat'
    self._gsutil = self.PathJoin(self._script_dir, gsutil)

    # Scripts in the chromium scripts dir.
    self._process_coverage_tool = J(s_dir, 'process_coverage.py')
    self._layout_archive_tool = J(s_dir, 'archive_layout_test_results.py')
    self._package_source_tool = J(s_dir, 'package_source.py')
    self._crash_handler_tool = J(s_dir, 'run_crash_handler.py')
    self._upload_parity_tool = J(s_dir, 'upload_parity_data.py')
    self._target_tests_tool = J(s_dir, 'target-tests.py')
    self._layout_test_tool = J(s_dir, 'layout_test_wrapper.py')
    self._lint_test_files_tool = J(s_dir, 'lint_test_files_wrapper.py')
    self._test_webkitpy_tool = J(s_dir, 'test_webkitpy_wrapper.py')
    self._archive_coverage = J(s_dir, 'archive_coverage.py')
    self._gpu_archive_tool = J(s_dir, 'archive_gpu_pixel_test_results.py')
    self._cf_archive_tool = J(s_dir, 'cf_archive_build.py')
    self._archive_tool = J(s_dir, 'archive_build.py')
    self._sizes_tool = J(s_dir, 'sizes.py')
    self._check_lkgr_tool = J(s_dir, 'check_lkgr.py')
    self._windows_syzyasan_tool = J(s_dir, 'win_apply_syzyasan.py')
    self._dynamorio_coverage_tool = J(s_dir, 'dynamorio_coverage.py')
    self._checkbins_tool = J(s_dir, 'checkbins_wrapper.py')
    self._mini_installer_tests_tool = J(s_dir, 'test_mini_installer_wrapper.py')
    self._device_status_check = J(self._bb_dir, 'bb_device_status_check.py')

    # Scripts in the private dir.
    self._download_and_extract_official_tool = self.PathJoin(
        p_dir, 'get_official_build.py')

    # These scripts should be move to the script dir.
    self._check_deps_tool = J('src', 'tools', 'checkdeps', 'checkdeps.py')
    self._check_perms_tool = J('src', 'tools', 'checkperms', 'checkperms.py')
    self._check_licenses_tool = J('src', 'tools', 'checklicenses',
                                  'checklicenses.py')
    self._posix_memory_tests_runner = J('src', 'tools', 'valgrind',
                                        'chrome_tests.sh')
    self._win_memory_tests_runner = J('src', 'tools', 'valgrind',
                                      'chrome_tests.bat')
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

    self._telemetry_tool = self.PathJoin(self._script_dir, 'telemetry.py')
    self._telemetry_unit_tests = J('src', 'tools', 'telemetry', 'run_tests')
    self._telemetry_perf_unit_tests = J('src', 'tools', 'perf', 'run_tests')

    # Virtual webcam check script.
    self._virtual_webcam_script = J(self._script_dir, 'webrtc',
                                    'ensure_webcam_is_running.py')

  def AddArchiveStep(self, data_description, base_url, link_text, command,
                     more_link_url=None, more_link_text=None,
                     index_suffix='', include_last_change=True):
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
                          index_suffix=index_suffix,
                          include_last_change=include_last_change)

  # TODO(stip): not sure if this is relevant for new perf dashboard.
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

  def AddGenerateCodeTallyStep(self, dll):
    """Adds a step to run code tally over the given dll."""
    launcher = self.PathJoin(self._script_dir, 'syzygy', 'script_launcher.py')
    code_tally_exe = self.PathJoin('src', 'third_party', 'syzygy', 'binaries',
                                   'exe', 'experimental', 'code_tally.exe')
    code_tally_json = self.PathJoin('@{BUILD_DIR}', self._target,
                                    '%s_code_tally.json' % dll)
    dll_path = self.PathJoin('@{BUILD_DIR}', self._target, dll)

    cmd = [self._python, launcher,
           code_tally_exe,
           '--input-image=%s' % dll_path,
           '--output-file=%s' % code_tally_json]

    self._factory.addStep(shell.ShellCommand,
                          name='%s_code_tally' % dll,
                          description='%s_code_tally' % dll,
                          command=cmd)

  def AddConvertCodeTallyJsonStep(self, dll):
    """Adds a step to convert the json file to the required server format."""
    launcher = self.PathJoin(self._script_dir, 'syzygy', 'script_launcher.py')
    convert_code_tally = self.PathJoin('src', 'third_party', 'syzygy',
                                       'binaries', 'exe', 'experimental',
                                       'convert_code_tally.py')
    code_tally_json = self.PathJoin('@{BUILD_DIR}', self._target,
                                    '%s_code_tally.json' % dll)
    converted_code_tally = self.PathJoin('@{BUILD_DIR}', self._target,
                                         '%s_converted_code_tally.json' % dll)

    cmd = [self._python, launcher,
           self._python, convert_code_tally,
           '--master_id', WithProperties('%(mastername)s'),
           '--builder_name', WithProperties('%(buildername)s'),
           '--build_number', WithProperties('%(buildnumber)s'),
           '--revision', WithProperties('%(got_revision)s'),
           code_tally_json,
           converted_code_tally]

    self._factory.addStep(shell.ShellCommand,
                          name='convert_%s_code_tally' % dll,
                          description='convert_%s_code_tally' % dll,
                          command=cmd)

  def AddUploadConvertedCodeTally(self, dll, upload_url):
    """Adds a step to upload the converted json file to the dashboard."""
    launcher = self.PathJoin(self._script_dir, 'syzygy', 'script_launcher.py')
    upload_script = self.PathJoin(self._script_dir, 'syzygy',
                                  'upload_code_tally.py')
    converted_code_tally = self.PathJoin('@{BUILD_DIR}', self._target,
                                         '%s_converted_code_tally.json' % dll)

    cmd = [self._python, launcher,
           self._python, upload_script,
           upload_url,
           converted_code_tally]

    self._factory.addStep(shell.ShellCommand,
                          name='upload_%s_code_tally' % dll,
                          description='upload_%s_code_tally' % dll,
                          command=cmd)

  def AddWindowsSyzyASanStep(self):
    """Adds a step to run syzyASan over the output directory."""
    cmd = [self._python, self._windows_syzyasan_tool,
           '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'apply_syzyasan', cmd)

  def AddArchiveBuild(self, mode='dev', show_url=True, factory_properties=None):
    """Adds a step to the factory to archive a build."""

    extra_archive_paths = factory_properties.get('extra_archive_paths')
    use_build_number = factory_properties.get('use_build_number', False)
    build_name = factory_properties.get('build_name')

    if show_url:
      (url, index_suffix) = _GetSnapshotUrl(factory_properties)
      text = 'download'
    else:
      url = None
      index_suffix = None
      text = None

    cmd = [self._python, self._archive_tool,
           '--target', self._target,
           '--mode', mode]
    if extra_archive_paths:
      cmd.extend(['--extra-archive-paths', extra_archive_paths])
    if use_build_number:
      cmd.extend(['--build-number', WithProperties('%(buildnumber)s')])
    if build_name:
      cmd.extend(['--build-name', build_name])

    gclient_env = (factory_properties or {}).get('gclient_env', {})
    if 'target_arch=arm' in gclient_env.get('GYP_DEFINES', ''):
      cmd.extend(['--arch', 'arm'])

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self.AddArchiveStep(data_description='build', base_url=url, link_text=text,
                        command=cmd, index_suffix=index_suffix)

  def AddCFArchiveBuild(self, factory_properties=None):
    """Adds a step to the factory to archive a ClusterFuzz build."""

    cmd = [self._python, self._cf_archive_tool,
           '--target', self._target]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self.AddTestStep(retcode_command.ReturnCodeCommand,
                     'ClusterFuzz Archive', cmd)

  def AddPackageSource(self, factory_properties=None):
    """Adds a step to the factory to package and upload the source directory."""
    factory_properties = factory_properties or {}
    factory_properties.setdefault('package_filename', 'chromium-src')

    cmd = [self._python, self._package_source_tool]

    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)

    self._factory.addStep(archive_command.ArchiveCommand,
                          name='package_source',
                          timeout=1200,
                          maxTime=10*60*60,
                          description='packaging source',
                          descriptionDone='packaged source',
                          base_url=None,
                          link_text=None,
                          more_link_url=None,
                          more_link_text=None,
                          command=cmd)

  def GetAnnotatedPerfCmd(self, gtest_filter, log_type, test_name,
                          cmd_name, tool_opts=None,
                          options=None, factory_properties=None,
                          py_script=False, dashboard_url=None):
    """Return a runtest command suitable for most perf test steps."""

    dashboard_url = dashboard_url or config.Master.dashboard_upload_url

    tool_options = ['--annotate=' + log_type]
    tool_options.extend(tool_opts or [])
    tool_options.append('--results-url=%s' % dashboard_url)

    arg_list = options or []
    if gtest_filter:
      arg_list += ['--gtest_filter=' + gtest_filter]

    factory_properties = factory_properties or {}
    factory_properties['test_name'] = test_name

    perf_id = factory_properties.get('perf_id')
    show_results = factory_properties.get('show_perf_results')

    perf_name = self._PerfStepMappings(show_results,
                                       perf_id)
    factory_properties['perf_name'] = perf_name

    if py_script:
      return self.GetPythonTestCommand(cmd_name, wrapper_args=tool_options,
                                       arg_list=arg_list,
                                       factory_properties=factory_properties)
    else:
      arg_list.extend([
          # Prevents breakages in perf tests, but we shouldn't have to set this.
          # TODO(phajdan.jr): Do not set this.
          '--single-process-tests',
          ])

      return self.GetTestCommand(cmd_name, wrapper_args=tool_options,
                                 arg_list=arg_list,
                                 factory_properties=factory_properties)

  def AddAnnotatedPerfStep(self, test_name, gtest_filter, log_type,
                           factory_properties, cmd_name,
                           tool_opts=None, cmd_options=None, step_name=None,
                           timeout=1200, py_script=False, dashboard_url=None,
                           addmethod=None, alwaysRun=False):

    """Add an annotated perf step to the builder.

    Args:
      test_name: name of the test given to runtest.py. If step_name is not
        provided, a standard transform will be applied and the step on the
        waterfall will be test_name_test.

      gtest_filter: most steps use --gtest_filter to filter their output.

      log_type: one of the log parsers in runtest.py --annotate=list, such
        as 'graphing' or 'framerate'.

      cmd_name: command to run.

      tool_opts: additional options for runtest.py.

      cmd_options: additional options for the test run under runtest.py.

      step_name: the step name for the builder/waterfall.

      factory_properties: additional properties from the factory.
    """

    step_name = step_name or test_name.replace('-', '_') + '_test'
    factory_properties = factory_properties.copy()
    factory_properties['step_name'] = factory_properties.get('step_name',
                                                             step_name)
    addmethod = addmethod or self.AddTestStep

    cmd = self.GetAnnotatedPerfCmd(gtest_filter, log_type, test_name,
                                   cmd_name=cmd_name, options=cmd_options,
                                   tool_opts=tool_opts,
                                   factory_properties=factory_properties,
                                   py_script=py_script,
                                   dashboard_url=dashboard_url)

    addmethod(chromium_step.AnnotatedCommand, step_name, cmd,
              do_step_if=self.TestStepFilter, target=self._target,
              factory_properties=factory_properties, timeout=timeout,
              alwaysRun=alwaysRun)

  def AddBuildrunnerAnnotatedPerfStep(self, *args, **kwargs):
    """Add annotated step to be run by buildrunner."""
    kwargs.setdefault('addmethod', self.AddBuildrunnerTestStep)
    self.AddAnnotatedPerfStep(*args, **kwargs)

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
    cmd = [self._python, self._checkbins_tool, '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'check_bins', cmd,
                     do_step_if=self.TestStepFilter)

  def AddVirtualWebcamCheck(self):
    cmd = [self._python, self._virtual_webcam_script]
    self.AddTestStep(shell.ShellCommand, 'ensure_virtual_webcam_is_up', cmd,
                     do_step_if=self.TestStepFilter, usePTY=False)

  def AddBuildrunnerCheckBinsStep(self):
    cmd = [self._python, self._checkbins_tool, '--target', self._target]
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
    self.AddAnnotatedPerfStep(
        'mach_ports', 'MachPortsTest.*', 'graphing',
        cmd_name='performance_browser_tests',
        cmd_options=['--test-launcher-print-test-stdio=always'],
        step_name='mach_ports',
        factory_properties=factory_properties)

  def AddCCPerfTests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('cc_perftests', None, 'graphing',
                              cmd_name='cc_perftests',
                              step_name='cc_perftests',
                              factory_properties=factory_properties)

  def AddMediaPerfTests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('media_perftests', None, 'graphing',
                              cmd_name='media_perftests',
                              step_name='media_perftests',
                              factory_properties=factory_properties)

  def AddLoadLibraryPerfTests(self, factory_properties=None):
    self.AddAnnotatedPerfStep('load_library_perf_tests', None, 'graphing',
                              cmd_name='load_library_perf_tests',
                              step_name='load_library_perf_tests',
                              factory_properties=factory_properties)

  def AddSizesTests(self, factory_properties=None):
    factory_properties = factory_properties or {}

    # For Android, platform is hardcoded as target_platform is set to linux2.
    # By default, the sizes.py script looks at sys.platform to identify
    # the platform (which is also linux2).
    args = ['--target', self._target]

    if self._target_os == 'android':
      args.extend(['--platform', 'android'])

    self.AddAnnotatedPerfStep('sizes', None, 'graphing', step_name='sizes',
                              cmd_name = self._sizes_tool, cmd_options=args,
                              py_script=True,
                              factory_properties=factory_properties)

  def AddBuildrunnerSizesTests(self, factory_properties=None):
    factory_properties = factory_properties or {}

    # For Android, platform is hardcoded as target_platform is set to linux2.
    # By default, the sizes.py script looks at sys.platform to identify
    # the platform (which is also linux2).
    args = ['--target', self._target]

    if self._target_os == 'android':
      args.extend(['--platform', 'android'])

    self.AddBuildrunnerAnnotatedPerfStep('sizes', None, 'graphing',
        step_name='sizes', cmd_name = self._sizes_tool, cmd_options=args,
        py_script=True, factory_properties=factory_properties)

  def AddTabCapturePerformanceTests(self, factory_properties=None):
    options = ['--enable-gpu']
    tool_options = ['--no-xvfb']

    self.AddAnnotatedPerfStep('tab_capture_performance',
                              'TabCapturePerformanceTest*', 'graphing',
                              cmd_name='performance_browser_tests',
                              step_name='tab_capture_performance_tests',
                              cmd_options=options,
                              tool_opts=tool_options,
                              factory_properties=factory_properties)

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

  def AddTelemetryUnitTests(self):
    step_name = 'telemetry_unittests'
    if self._target_os == 'android':
      args = ['--browser=android-content-shell']
    else:
      args = ['--browser=%s' % self._target.lower()]
    cmd = self.GetPythonTestCommand(self._telemetry_unit_tests,
                                    arg_list=args,
                                    wrapper_args=['--annotate=gtest',
                                                  '--test-type=%s' % step_name])

    self.AddTestStep(chromium_step.AnnotatedCommand, step_name, cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerTelemetryUnitTests(self):
    step_name = 'telemetry_unittests'
    if self._target_os == 'android':
      args = ['--browser=android-content-shell']
    else:
      args = ['--browser=%s' % self._target.lower()]
    cmd = self.GetPythonTestCommand(self._telemetry_unit_tests,
                                    arg_list=args,
                                    wrapper_args=['--annotate=gtest',
                                                  '--test-type=%s' % step_name])

    self.AddBuildrunnerTestStep(chromium_step.AnnotatedCommand, step_name, cmd,
                                do_step_if=self.TestStepFilter)

  def AddTelemetryPerfUnitTests(self):
    step_name = 'telemetry_perf_unittests'
    if self._target_os == 'android':
      args = ['--browser=android-content-shell']
    else:
      args = ['--browser=%s' % self._target.lower()]
    cmd = self.GetPythonTestCommand(self._telemetry_perf_unit_tests,
                                    arg_list=args,
                                    wrapper_args=['--annotate=gtest',
                                                  '--test-type=%s' % step_name])

    self.AddTestStep(chromium_step.AnnotatedCommand, step_name, cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerTelemetryPerfUnitTests(self):
    step_name = 'telemetry_perf_unittests'
    if self._target_os == 'android':
      args = ['--browser=android-content-shell']
    else:
      args = ['--browser=%s' % self._target.lower()]
    cmd = self.GetPythonTestCommand(self._telemetry_perf_unit_tests,
                                    arg_list=args,
                                    wrapper_args=['--annotate=gtest',
                                                  '--test-type=%s' % step_name])

    self.AddBuildrunnerTestStep(chromium_step.AnnotatedCommand, step_name, cmd,
                                do_step_if=self.TestStepFilter)

  def AddInstallerTests(self, factory_properties):
    if self._target_platform == 'win32':
      self.AddGTestTestStep('installer_util_unittests',
                            factory_properties)
      if (self._target == 'Release' and
          not factory_properties.get('disable_mini_installer_test')):
        self.AddGTestTestStep('mini_installer_test',
                              factory_properties,
                              arg_list=['-clean'])

  def AddBuildrunnerInstallerTests(self, factory_properties):
    if self._target_platform == 'win32':
      self.AddGTestTestStep('installer_util_unittests',
                            factory_properties)
      if (self._target == 'Release' and
          not factory_properties.get('disable_mini_installer_test')):
        self.AddBuildrunnerGTest('mini_installer_test',
                                 factory_properties,
                                 arg_list=['-clean'])

  def AddChromeUnitTests(self, factory_properties):
    self.AddGTestTestStep('ipc_tests', factory_properties)
    self.AddGTestTestStep('sync_unit_tests', factory_properties)
    self.AddGTestTestStep('unit_tests', factory_properties)
    self.AddGTestTestStep('sql_unittests', factory_properties)
    self.AddGTestTestStep('ui_unittests', factory_properties)
    self.AddGTestTestStep('content_unittests', factory_properties)
    if self._target_platform == 'win32':
      self.AddGTestTestStep('views_unittests', factory_properties)

  def AddBuildrunnerChromeUnitTests(self, factory_properties):
    self.AddBuildrunnerGTest('ipc_tests', factory_properties)
    self.AddBuildrunnerGTest('sync_unit_tests', factory_properties)
    self.AddBuildrunnerGTest('unit_tests', factory_properties)
    self.AddBuildrunnerGTest('sql_unittests', factory_properties)
    self.AddBuildrunnerGTest('ui_unittests', factory_properties)
    self.AddBuildrunnerGTest('content_unittests', factory_properties)
    if self._target_platform == 'win32':
      self.AddBuildrunnerGTest('views_unittests', factory_properties)

  def AddSyncIntegrationTests(self, factory_properties):
    options = ['--ui-test-action-max-timeout=120000']

    self.AddGTestTestStep('sync_integration_tests',
                          factory_properties, '',
                          options)

  def AddBuildrunnerSyncIntegrationTests(self, factory_properties):
    options = ['--ui-test-action-max-timeout=120000']

    self.AddBuildrunnerGTest('sync_integration_tests',
                             factory_properties, '',
                             options)

  def AddBrowserTests(self, factory_properties=None):
    description = ''
    options = ['--lib=browser_tests']

    total_shards = factory_properties.get('browser_total_shards')
    shard_index = factory_properties.get('browser_shard_index')
    options.append(factory_properties.get('browser_tests_filter', []))

    options = filter(None, options)

    self.AddGTestTestStep('browser_tests', factory_properties,
                          description, options,
                          total_shards=total_shards,
                          shard_index=shard_index)

  def AddPushCanaryTests(self, factory_properties=None):
    description = ''
    options = ['--lib=browser_tests']
    options.append('--run_manual')
    total_shards = factory_properties.get('browser_total_shards')
    shard_index = factory_properties.get('browser_shard_index')
    options.append('--gtest_filter=PushMessagingCanaryTest.*')
    options.append('--password-file-for-test=' +
                   '/usr/local/google/work/chromium/test_pass1.txt')
    options.append('--override-user-data-dir=' +
                   '/usr/local/google/work/chromium/foo')
    options.append('--ui-test-action-timeout=120000')
    options.append('--v=2')

    self.AddGTestTestStep('browser_tests', factory_properties,
                          description, options,
                          total_shards=total_shards,
                          shard_index=shard_index)

  def AddBuildrunnerBrowserTests(self, factory_properties):
    description = ''
    options = ['--lib=browser_tests']

    total_shards = factory_properties.get('browser_total_shards')
    shard_index = factory_properties.get('browser_shard_index')
    options.append(factory_properties.get('browser_tests_filter', []))
    options.extend(factory_properties.get('browser_tests_extra_options', []))

    options = filter(None, options)

    self.AddBuildrunnerGTest('browser_tests', factory_properties,
                             description, options,
                             total_shards=total_shards,
                             shard_index=shard_index)

  def AddMemoryTest(self, test_name, tool_name, timeout=1200,
                    factory_properties=None,
                    wrapper_args=None, addmethod=None):
    factory_properties = factory_properties or {}
    factory_properties['full_test_name'] = True
    if not wrapper_args:
      wrapper_args = []
    wrapper_args.extend([
        '--annotate=gtest',
        '--test-type', 'memory test: %s' % test_name,
        '--pass-build-dir',
        '--pass-target',
    ])
    command_class = chromium_step.AnnotatedCommand
    addmethod = addmethod or self.AddTestStep

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

    # Memory tests runner script path is relative to build dir.
    if self._target_platform != 'win32':
      runner = os.path.join('..', '..', '..', self._posix_memory_tests_runner)
    else:
      runner = os.path.join('..', '..', '..', self._win_memory_tests_runner)

    cmd = self.GetShellTestCommand(runner, arg_list=[
        '--test', test_name,
        '--tool', tool_name],
        wrapper_args=wrapper_args,
        factory_properties=factory_properties)

    test_name = 'memory test: %s' % test_name
    addmethod(command_class, test_name, cmd,
              timeout=timeout,
              do_step_if=self.TestStepFilter)

  def AddBuildrunnerMemoryTest(self, *args, **kwargs):
    """Add a memory test using buildrunner."""
    kwargs.setdefault('addmethod', self.AddBuildrunnerTestStep)
    self.AddMemoryTest(*args, **kwargs)

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

  def AddDeviceStatus(self, factory_properties=None):
    """Reports the status of the bot devices."""
    factory_properties = factory_properties or {}

    self.AddBuildrunnerAnnotatedPerfStep(
      'device_status', None, 'graphing',
      cmd_name=self._device_status_check,
      cmd_options=['--device-status-dashboard'], step_name='device_status',
      py_script=True, factory_properties=factory_properties, alwaysRun=True)

  def AddTelemetryTest(self, test_name, step_name=None,
                       factory_properties=None, timeout=1200,
                       tool_options=None, dashboard_url=None):
    """Adds a Telemetry performance test.

    Args:
      test_name: The name of the benchmark module to run.
      step_name: The name used to build the step's logfile name and descriptions
          in the waterfall display. Defaults to |test_name|.
      factory_properties: A dictionary of factory property values.
    """
    step_name = step_name or test_name

    factory_properties = (factory_properties or {}).copy()
    factory_properties['test_name'] = test_name
    factory_properties['target'] = self._target
    factory_properties['target_os'] = self._target_os
    factory_properties['target_platform'] = self._target_platform
    factory_properties['step_name'] = factory_properties.get('step_name',
                                                             step_name)

    cmd_options = self.AddFactoryProperties(factory_properties)

    log_type = 'graphing'
    if test_name.split('.')[0] == 'page_cycler':
      log_type = 'pagecycler'
    if test_name.split('.')[0] == 'endure':
      log_type = 'endure'

    self.AddAnnotatedPerfStep(step_name, None, log_type, factory_properties,
                              cmd_name=self._telemetry_tool,
                              cmd_options=cmd_options,
                              step_name=step_name, timeout=timeout,
                              tool_opts=tool_options, py_script=True,
                              dashboard_url=dashboard_url)

  def AddBisectTest(self):
    """Adds a step to the factory to run a bisection on a range of revisions
    to investigate performance regressions."""

    # Need to run this in advance to create the depot and sync
    # the appropriate directories so that apache will launch correctly.
    cmd_name = self.PathJoin('src', 'tools',
                             'prepare-bisect-perf-regression.py')
    cmd = [self._python, cmd_name, '-w', '.']
    self.AddTestStep(chromium_step.AnnotatedCommand, 'Preparing for Bisection',
                     cmd)

    cmd_name = self.PathJoin('src', 'tools', 'run-bisect-perf-regression.py')
    cmd_args = ['-w', '.', '-p', self.PathJoin('..', '..', '..', 'goma')]
    cmd = self.GetPythonTestCommand(cmd_name, arg_list=cmd_args)
    self.AddTestStep(chromium_step.AnnotatedCommand, 'Running Bisection',
        cmd, timeout=30*60, max_time=12*60*60)

  def AddWebkitLint(self, factory_properties=None):
    """Adds a step to the factory to lint the test_expectations.txt file."""
    cmd = [self._python, self._lint_test_files_tool,
           '--target', self._target]
    self.AddTestStep(shell.ShellCommand,
                     test_name='webkit_lint',
                     test_command=cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerWebkitLint(self, factory_properties=None):
    """Adds a step to the factory to lint the test_expectations.txt file."""
    cmd = [self._python, self._lint_test_files_tool,
           '--target', self._target]
    self.AddBuildrunnerTestStep(shell.ShellCommand,
                                test_name='webkit_lint',
                                test_command=cmd,
                                do_step_if=self.TestStepFilter)

  def AddWebkitPythonTests(self, factory_properties=None):
    """Adds a step to the factory to run test-webkitpy."""
    cmd = [self._python, self._test_webkitpy_tool,
           '--target', self._target]
    self.AddTestStep(shell.ShellCommand,
                     test_name='webkit_python_tests',
                     test_command=cmd,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerWebkitPythonTests(self, factory_properties=None):
    """Adds a step to the factory to run test-webkitpy."""
    cmd = [self._python, self._test_webkitpy_tool,
           '--target', self._target]
    self.AddBuildrunnerTestStep(shell.ShellCommand,
                                test_name='webkit_python_tests',
                                test_command=cmd,
                                do_step_if=self.TestStepFilter)

  def AddWebRTCTests(self, tests, factory_properties, timeout=1200):
    """Adds a list of tests, possibly prefixed for running within a tool.

    To run a test under memcheck, prefix the test name with 'memcheck_'.
    To run a test under tsan, prefix the test name with 'tsan_'.
    The following prefixes are supported:
    - 'memcheck_' for memcheck
    - 'tsan_' for Thread Sanitizer (tsan)
    - 'tsan_gcc_' for Thread Sanitizer (GCC)
    - 'tsan_rv_' for Thread Sanitizer (RaceVerifier)
    - 'drmemory_full_' for Dr Memory (full)
    - 'drmemory_light_' for Dr Memory (light)
    - 'drmemory_pattern_' for Dr Memory (pattern)

    To run a test with perf measurements; add a key 'perf_measuring_tests'
    mapped to a list of test names in the factory properties.

    To run a test using the buildbot_tests.py script in WebRTC; add a key
    'custom_cmd_line_tests' mapped to a list of test names in the factory
    properties.

    Args:
      tests: List of test names, possibly prefixed as described above.
      factory_properties: Dict of properties to be used during execution.
      timeout: Max time a test may run before it is killed.
    """

    def M(test, prefix, fp, timeout):
      """If the prefix matches the test name it is added and True is returned.
      """
      if test.startswith(prefix):
        # Normally buildrunner tests would be added in chromium_factory. We need
        # to add that logic here since we're in chromium_commands.
        if test.endswith('_br'):
          real_test = test[:-3]
          self.AddBuildrunnerMemoryTest(
              real_test[len(prefix):], prefix[:-1], timeout, fp)
        else:
          self.AddMemoryTest(test[len(prefix):], prefix[:-1], timeout, fp)
        return True
      return False

    def IsPerf(test_name, factory_properties):
      perf_measuring_tests = factory_properties.get('perf_measuring_tests', [])
      return test_name in perf_measuring_tests

    custom_cmd_line_tests = factory_properties.get('custom_cmd_line_tests', [])
    for test in tests:
      if M(test, 'memcheck_', factory_properties, timeout):
        continue
      if M(test, 'tsan_rv_', factory_properties, timeout):
        continue
      if M(test, 'tsan_', factory_properties, timeout):
        continue
      if M(test, 'drmemory_full_', factory_properties, timeout):
        continue
      if M(test, 'drmemory_light_', factory_properties, timeout):
        continue
      if M(test, 'drmemory_pattern_', factory_properties, timeout):
        continue

      if test in custom_cmd_line_tests:
        # This hardcoded path is not pretty but it's better than duplicating
        # the output-path-finding code that only seems to exist in runtest.py.
        test_run_script = 'src/out/%s/buildbot_tests.py' % self._target
        args_list = ['--test', test]
        if IsPerf(test, factory_properties):
          self.AddAnnotatedPerfStep(test_name=test, gtest_filter=None,
                                    log_type='graphing',
                                    factory_properties=factory_properties,
                                    cmd_name=test_run_script,
                                    cmd_options=args_list, step_name=test,
                                    py_script=True)
        else:
          cmd = self.GetPythonTestCommand(test_run_script, arg_list=args_list)
          self.AddTestStep(chromium_step.AnnotatedCommand, test, cmd)
      else:
        if IsPerf(test, factory_properties):
          self.AddAnnotatedPerfStep(test_name=test, gtest_filter=None,
                                    log_type='graphing',
                                    factory_properties=factory_properties,
                                    cmd_name=test)
        else:
          self.AddGTestTestStep(test_name=test,
                                factory_properties=factory_properties)

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
      webkit_test_options: A list of additional options passed to
          run-webkit-tests. The list [o1, o2, ...] will be passed as a
          space-separated string 'o1 o2 ...'.
      layout_tests: List of layout tests to run.
    """
    factory_properties = factory_properties or {}
    with_pageheap = factory_properties.get('webkit_pageheap')
    archive_results = factory_properties.get('archive_webkit_results')
    layout_part = factory_properties.get('layout_part')
    test_results_server = factory_properties.get('test_results_server')
    enable_hardware_gpu = factory_properties.get('enable_hardware_gpu')
    layout_tests = factory_properties.get('layout_tests')
    time_out_ms = factory_properties.get('time_out_ms')
    driver_name = factory_properties.get('driver_name')
    additional_drt_flag = factory_properties.get('additional_drt_flag')
    webkit_test_options = factory_properties.get('webkit_test_options')

    builder_name = '%(buildername)s'
    result_str = 'results'
    test_name = 'webkit_tests'

    pageheap_description = ''
    if with_pageheap:
      pageheap_description = ' (--enable-pageheap)'

    webkit_result_dir = '/'.join(['..', '..', 'layout-test-results'])

    cmd_args = ['--target', self._target,
                '-o', webkit_result_dir,
                '--build-number', WithProperties('%(buildnumber)s'),
                '--builder-name', WithProperties(builder_name)]

    for comps in factory_properties.get('additional_expectations', []):
      cmd_args.append('--additional-expectations')
      cmd_args.append(self.PathJoin('src', *comps))

    if layout_part:
      cmd_args.extend(['--run-part', layout_part])

    if with_pageheap:
      cmd_args.append('--enable-pageheap')

    if test_results_server:
      cmd_args.extend(['--test-results-server', test_results_server])

    if time_out_ms:
      cmd_args.extend(['--time-out-ms', time_out_ms])

    if driver_name:
      cmd_args.extend(['--driver-name', driver_name])

    if additional_drt_flag:
      cmd_args.extend(['--additional-drt-flag', additional_drt_flag])

    additional_options = []
    if webkit_test_options:
      additional_options.extend(webkit_test_options)

    if enable_hardware_gpu:
      additional_options.append('--enable-hardware-gpu')

    if additional_options:
      cmd_args.append('--options=' + ' '.join(additional_options))

    # The list of tests is given as arguments.
    if layout_tests:
      cmd_args.extend(layout_tests)

    cmd = self.GetPythonTestCommand(self._layout_test_tool,
                                    cmd_args,
                                    wrapper_args=['--no-xvfb'],
                                    factory_properties=factory_properties)

    self.AddTestStep(webkit_test_command.WebKitCommand,
                     test_name=test_name,
                     test_description=pageheap_description,
                     test_command=cmd,
                     do_step_if=self.TestStepFilter)

    if archive_results:
      gs_bucket = 'chromium-layout-test-archives'
      factory_properties['gs_bucket'] = 'gs://' + gs_bucket
      cmd = [self._python, self._layout_archive_tool,
             '--results-dir', webkit_result_dir,
             '--build-number', WithProperties('%(buildnumber)s'),
             '--builder-name', WithProperties(builder_name)]

      cmd = self.AddBuildProperties(cmd)
      cmd = self.AddFactoryProperties(factory_properties, cmd)

      base_url = ("https://storage.googleapis.com/" +
                  gs_bucket + "/%(build_name)s" )
      self.AddArchiveStep(
          data_description='webkit_tests ' + result_str,
          base_url=base_url,
          link_text='layout test ' + result_str,
          command=cmd,
          include_last_change=False,
          index_suffix='layout-test-results/results.html',
          more_link_text='(zip)',
          more_link_url='layout-test-results.zip')

  def AddRunCrashHandler(self, build_dir=None, target=None):
    target = target or self._target
    cmd = [self._python, self._crash_handler_tool, '--target', target]
    self.AddTestStep(shell.ShellCommand, 'start_crash_handler', cmd)

  def AddProcessDumps(self):
    cmd = [self._python, self._process_dumps_tool,
           '--target', self._target]
    self.AddTestStep(retcode_command.ReturnCodeCommand, 'process_dumps', cmd)

  def AddProcessCoverage(self, factory_properties=None):
    factory_properties = factory_properties or {}

    args = ['--target', self._target,
            '--build-id', WithProperties('%(got_revision)s')]
    if factory_properties.get('test_platform'):
      args += ['--platform', factory_properties.get('test_platform')]
    if factory_properties.get('upload-dir'):
      args += ['--upload-dir', factory_properties.get('upload-dir')]

    args = self.AddFactoryProperties(factory_properties, args)

    self.AddAnnotatedPerfStep('coverage', None, 'graphing',
                              step_name='process_coverage',
                              cmd_name=self._process_coverage_tool,
                              cmd_options=args, py_script=True,
                              factory_properties=factory_properties)

    # Map the perf ID to the coverage subdir, so we can link from the coverage
    # graph
    perf_mapping = self.PERF_TEST_MAPPINGS[self._target]
    perf_id = factory_properties.get('perf_id')
    perf_subdir = perf_mapping.get(perf_id)

    # 'total_coverage' is the default archive_folder for
    # archive_coverage.py script.
    url = _GetArchiveUrl('coverage', perf_subdir) + '/total_coverage'
    text = 'view coverage'
    cmd_archive = [self._python, self._archive_coverage,
                   '--target', self._target,
                   '--perf-subdir', perf_subdir]
    if factory_properties.get('use_build_number'):
      cmd_archive.extend(['--build-number', WithProperties('%(buildnumber)s')])

    self.AddArchiveStep(data_description='coverage', base_url=url,
                        link_text=text, command=cmd_archive)

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

  def AddGpuContentTests(self, factory_properties):
    """Runs content_browsertests binary with selected gpu tests.

    This binary contains content side browser tests that should be run on the
    gpu bots.
    """
    # Put gpu data in /b/build/slave/SLAVE_NAME/gpu_data
    gpu_data = self.PathJoin('..', 'content_gpu_data')
    gen_dir = self.PathJoin(gpu_data, 'generated')
    ref_dir = self.PathJoin(gpu_data, 'reference')

    revision_arg = WithProperties('--build-revision=%(got_revision)s')

    tests = ':'.join(['WebGLConformanceTest.*', 'Gpu*.*'])

    self.AddGTestTestStep('content_browsertests', factory_properties,
                          arg_list=['--use-gpu-in-tests',
                                    '--generated-dir=%s' % gen_dir,
                                    '--reference-dir=%s' % ref_dir,
                                    revision_arg,
                                    '--gtest_filter=%s' % tests,
                                    '--ui-test-action-max-timeout=45000',
                                    '--run-manual'],
                          test_tool_arg_list=['--no-xvfb'])

    # Setup environment for running gsutil, a Google Storage utility.
    env = {}
    env['GSUTIL'] = self._gsutil

    cmd = [self._python,
           self._gpu_archive_tool,
           '--run-id', WithProperties('%(got_revision)s_%(buildername)s'),
           '--generated-dir', gen_dir,
           '--gpu-reference-dir', ref_dir]
    self.AddTestStep(shell.ShellCommand, 'archive test results', cmd, env=env)

  def AddBuildrunnerGpuContentTests(self, factory_properties):
    """Runs content_browsertests with selected gpu tests under Buildrunner.

    This binary contains content side browser tests that should be run on the
    gpu bots.
    """
    # Put gpu data in /b/build/slave/SLAVE_NAME/gpu_data
    gpu_data = self.PathJoin('..', 'content_gpu_data')
    gen_dir = self.PathJoin(gpu_data, 'generated')
    ref_dir = self.PathJoin(gpu_data, 'reference')

    revision_arg = WithProperties('--build-revision=%(got_revision)s')

    tests = ':'.join(['WebGLConformanceTest.*', 'Gpu*.*'])

    self.AddBuildrunnerGTest('content_browsertests', factory_properties,
                          arg_list=['--use-gpu-in-tests',
                                    '--generated-dir=%s' % gen_dir,
                                    '--reference-dir=%s' % ref_dir,
                                    revision_arg,
                                    '--gtest_filter=%s' % tests,
                                    '--ui-test-action-max-timeout=45000',
                                    '--run-manual'],
                          test_tool_arg_list=['--no-xvfb'])

    # Setup environment for running gsutil, a Google Storage utility.
    env = {}
    env['GSUTIL'] = self._gsutil

    cmd = [self._python,
           self._gpu_archive_tool,
           '--run-id', WithProperties('%(got_revision)s_%(buildername)s'),
           '--generated-dir', gen_dir,
           '--gpu-reference-dir', ref_dir]
    self.AddBuildrunnerTestStep(shell.ShellCommand, 'archive test results', cmd,
                                env=env)

  def AddGLTests(self, factory_properties=None):
    """Runs gl_tests binary.

    This binary contains unit tests that should be run on the gpu bots.
    """
    factory_properties = factory_properties or {}

    self.AddGTestTestStep('gl_tests', factory_properties,
                          test_tool_arg_list=['--no-xvfb'])

  def AddContentGLTests(self, factory_properties=None):
    """Runs content_gl_tests binary.

    This binary contains unit tests from the content directory
    that should be run on the gpu bots.
    """
    factory_properties = factory_properties or {}

    self.AddGTestTestStep('content_gl_tests', factory_properties,
                          test_tool_arg_list=['--no-xvfb'])

  def AddGLES2ConformTest(self, factory_properties=None):
    """Runs gles2_conform_test binary.

    This binary contains the OpenGL ES 2.0 Conformance tests to be run on the
    gpu bots.
    """
    factory_properties = factory_properties or {}

    self.AddGTestTestStep('gles2_conform_test', factory_properties,
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

  def AddBuildrunnerNaClIntegrationTestStep(self, factory_properties,
          target=None, buildbot_preset=None, timeout=1200):
    target = target or self._target
    cmd = [self._python, self._nacl_integration_tester_tool,
           '--mode', target]
    if buildbot_preset is not None:
      cmd.extend(['--buildbot', buildbot_preset])

    self.AddBuildrunnerTestStep(chromium_step.AnnotatedCommand,
                                'nacl_integration', cmd, halt_on_failure=True,
                                timeout=timeout, do_step_if=self.TestStepFilter)

  def AddAnnotatedSteps(self, factory_properties, timeout=1200):
    factory_properties = factory_properties or {}
    cmd = [self.PathJoin(self._chromium_script_dir,
                         factory_properties.get('annotated_script', ''))]

    if os.path.splitext(cmd[0])[1] == '.py':
      cmd.insert(0, self._python)
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotated_steps',
                          description='annotated_steps',
                          timeout=timeout,
                          haltOnFailure=True,
                          command=cmd)

  def AddAnnotationStep(self, name, cmd, factory_properties=None, env=None,
                        timeout=6000, maxTime=8*60*60):
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

    if os.path.splitext(cmd[0])[1] == '.py':
      cmd.insert(0, self._python)
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name=name,
                          description=name,
                          timeout=timeout,
                          haltOnFailure=True,
                          command=cmd,
                          env=env,
                          maxTime=maxTime,
                          factory_properties=factory_properties)

  def AddWebRtcPerfManualContentBrowserTests(self, factory_properties=None):
    cmd_options = ['--run-manual', '--test-launcher-print-test-stdio=always']
    self.AddAnnotatedPerfStep(test_name='webrtc_manual_content_browsertests',
                              gtest_filter="WebRtc*",
                              log_type='graphing',
                              factory_properties=factory_properties,
                              cmd_name='content_browsertests',
                              cmd_options=cmd_options)

  def AddWebRtcPerfManualBrowserTests(self, factory_properties=None):
    # These tests needs --test-launcher-jobs=1 since some of them are not able
    # to run in parallel (due to the usage of the peerconnection server).
    cmd_options = ['--run-manual', '--ui-test-action-max-timeout=300000',
                   '--test-launcher-jobs=1',
                   '--test-launcher-print-test-stdio=always']
    self.AddAnnotatedPerfStep(test_name='webrtc_manual_browser_tests',
                              gtest_filter="WebRtc*",
                              log_type='graphing',
                              factory_properties=factory_properties,
                              cmd_name='browser_tests',
                              cmd_options=cmd_options)

  def AddMiniInstallerTestStep(self, factory_properties):
    cmd = [self._python, self._mini_installer_tests_tool,
           '--target', self._target]
    self.AddTestStep(chromium_step.AnnotatedCommand, 'test_mini_installer', cmd,
                     halt_on_failure=True, timeout=600,
                     do_step_if=self.TestStepFilter)

  def AddBuildrunnerMiniInstallerTestStep(self, factory_properties,
          target=None, buildbot_preset=None, timeout=1200):
    target = target or self._target
    cmd = [self._python, self._mini_installer_tests_tool,
           '--target', target]
    if buildbot_preset is not None:
      cmd.extend(['--buildbot', buildbot_preset])

    self.AddBuildrunnerTestStep(chromium_step.AnnotatedCommand,
                                'test_mini_installer', cmd,
                                halt_on_failure=True, timeout=timeout,
                                do_step_if=self.TestStepFilter)

  def AddTriggerSwarmingTests(self, run_default_swarm_tests,
                              factory_properties):
    """Prepares a build to be run on the builder specified by
    'swarming_triggered_builder'.

    1. Generates the hash for each .isolated file and saves it in the build
       property 'swarm_hashes'.
    2. Triggers a dependent build which will actually talk to the Swarming
       master.
    """
    self._factory.properties.setProperty(
        'run_default_swarm_tests', run_default_swarm_tests, 'BuildFactory')

    # This step sets the build property 'swarm_hashes'.
    self.AddGenerateIsolatedHashesStep(
        swarm_commands.TestStepFilterTriggerSwarm)

    # Trigger the swarming test builder. The only issue here is that
    # updateSourceStamp=False cannot be used because we want the user to get the
    # email, e.g. the blamelist to be properly set, but that causes any patch to
    # be caried over, which is annoying but benign.
    self._factory.addStep(commands.CreateTriggerStep(
        trigger_name=factory_properties['swarming_triggered_builder'],
        trigger_set_properties={
            'target_os': self._target_platform,
            'use_swarming_client_revision':
              WithProperties('%(got_swarming_client_revision:-)s'),
        },
        trigger_copy_properties=[
            # try_mail_notifier.py needs issue, patchset and rietveld to note in
            # its email which issue this build references to.
            'issue',
            'patchset',
            'rietveld',
            'run_default_swarm_tests',
            'swarm_hashes',
        ],
        do_step_if=swarm_commands.TestStepFilterTriggerSwarm))

  def AddTriggerCoverageTests(self, factory_properties):
    """Trigger coverage testers, wait for completion, then process coverage."""
    # Add trigger step.
    self._factory.addStep(trigger.Trigger(
        schedulerNames=[factory_properties.get('coverage_trigger')],
        updateSourceStamp=True,
        waitForFinish=True))

  def AddPreProcessCoverage(self, dynamorio_dir, factory_properties):
    """Prepare dynamorio before running coverage tests."""
    cmd = [self._python,
           self._dynamorio_coverage_tool,
           '--pre-process',
           '--dynamorio-dir', dynamorio_dir]
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self.AddTestStep(shell.ShellCommand,
                     'pre-process coverage', cmd,
                     timeout=900, halt_on_failure=True)

  def AddCreateCoverageFile(self, test, dynamorio_dir, factory_properties):
    # Create coverage file.
    cmd = [self._python,
           self._dynamorio_coverage_tool,
           '--post-process',
           '--build-id', WithProperties('%(got_revision)s'),
           '--platform', factory_properties['test_platform'],
           '--dynamorio-dir', dynamorio_dir,
           '--test-to-upload', test]
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self.AddTestStep(shell.ShellCommand,
                     'create_coverage_' + test, cmd,
                     timeout=900, halt_on_failure=True)

  def AddCoverageTests(self, factory_properties):
    """Add tests to run with dynamorio code coverage tool."""
    factory_properties['coverage_gtest_exclusions'] = True
    # TODO(thakis): Don't look at _build_dir here.
    dynamorio_dir = self.PathJoin(self._build_dir, 'dynamorio')
    ddrun_bin = self.PathJoin(dynamorio_dir, 'bin32',
                              self.GetExecutableName('drrun'))
    ddrun_cmd = [ddrun_bin, '-t', 'bbcov', '--']
    # Run browser tests with dynamorio environment vars.
    tests = factory_properties['tests']
    if 'browser_tests' in tests:
      browser_tests_prop = factory_properties.copy()
      browser_tests_prop['testing_env'] = {
          'BROWSER_WRAPPER': ' '.join(ddrun_cmd)}
      arg_list = ['--lib=browser_tests']
      arg_list += ['--ui-test-action-timeout=1200000',
                   '--ui-test-action-max-timeout=2400000',
                   '--ui-test-terminate-timeout=1200000']
      # Run single thread.
      arg_list += ['--jobs=1']
      arg_list = filter(None, arg_list)
      total_shards = factory_properties.get('browser_total_shards')
      shard_index = factory_properties.get('browser_shard_index')
      self.AddPreProcessCoverage(dynamorio_dir, browser_tests_prop)
      self.AddGTestTestStep('browser_tests',
                            browser_tests_prop,
                            description='',
                            arg_list=arg_list,
                            total_shards=total_shards,
                            shard_index=shard_index,
                            timeout=3*10*60,
                            max_time=24*60*60)
      self.AddCreateCoverageFile('browser_tests',
                                 dynamorio_dir,
                                 factory_properties)

    # Add all other tests without sharding.
    shard_index = factory_properties.get('browser_shard_index')
    if not shard_index or shard_index == 1:
      # TODO(thakis): Don't look at _build_dir here.
      test_path = self.PathJoin(self._build_dir, self._target)
      for test in tests:
        if test != 'browser_tests':
          cmd = ddrun_cmd + [self.PathJoin(test_path,
                             self.GetExecutableName(test))]
          self.AddPreProcessCoverage(dynamorio_dir, factory_properties)
          self.AddTestStep(shell.ShellCommand, test, cmd)
          self.AddCreateCoverageFile(test,
                                     dynamorio_dir,
                                     factory_properties)


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
