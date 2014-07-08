# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds Syzygy-specific commands."""

from buildbot.process.properties import WithProperties
from buildbot.steps import shell

from master import chromium_step
from master.factory import commands

class _UrlStatusCommand(shell.ShellCommand):
  """A ShellCommand subclass that adorns its build status with a URL on success.
  """
  def __init__(self, extra_text=None, **kw):
    """Initialize the buildstep.

    Args:
         extra_text: a tuple of (name, url) to pass to addUrl on successful
            completion.
    """
    self._extra_text = extra_text
    shell.ShellCommand.__init__(self, **kw)

    # Record our argument for the factory.
    self.addFactoryArguments(extra_text=extra_text)

  def commandComplete(self, cmd):
    """On success, add the URL provided to our status."""
    if cmd.rc == 0 and self._extra_text:
      (name, url) = self._extra_text
      self.addURL(self.build.render(name), self.build.render(url))


class SyzygyCommands(commands.FactoryCommands):
  """Encapsulates methods to add Syzygy commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None):
    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    self._arch = target_arch
    self._factory = factory

    # Build the path to the Python 2.6 runtime checked into Syzygy.
    self._syzygy_python_exe = self.PathJoin(
        self._repository_root, 'third_party', 'python_26', 'python.exe')

  def AddAppVerifierGTestTestStep(self, test_name):
    script_path = self.PathJoin(self._repository_root, 'syzygy',
                                'build', 'app_verifier.py')
    test_path = self.PathJoin(self._build_dir,
                              self._target,
                              test_name + '.exe')
    args = ['--on-waterfall', test_path, '--', '--gtest_print_time']
    wrapper_args = ['--annotate=gtest', '--test-type', test_name]

    command = self.GetPythonTestCommand(script_path, arg_list=args,
                                        wrapper_args=wrapper_args)

    self.AddTestStep(chromium_step.AnnotatedCommand, test_name, command)

  def AddRandomizeChromeStep(self):
    # Randomization script path.
    script_path = self.PathJoin(self._repository_root, 'syzygy',
                                'internal', 'build', 'randomize_chrome.py')
    command = [self._syzygy_python_exe, script_path,
               '--build-dir=%s' % self._build_dir,
               '--target=%s' % self._target,
               '--verbose']
    self.AddTestStep(shell.ShellCommand, 'randomly_reorder_chrome', command)

  def AddBenchmarkChromeStep(self):
    # Benchmark script path.
    script_path = self.PathJoin(self._repository_root, 'syzygy',
                                'internal', 'build', 'benchmark_chrome.py')
    command = [self._syzygy_python_exe, script_path,
               '--build-dir=%s' % self._build_dir,
               '--target=%s' % self._target,
               '--verbose']
    self.AddTestStep(shell.ShellCommand, 'benchmark_chrome', command)

  def AddGenerateCoverage(self):
    """Creates a step for generating a coverage report, archiving the results.
    """

    # Coverage script path.
    script_path = self.PathJoin(self._repository_root, 'syzygy', 'build',
                                'generate_coverage.py')

    # Generate the appropriate command line.
    command = [self._syzygy_python_exe,
               script_path,
               '--verbose',
               '--syzygy',
               '--build-dir',
               self.PathJoin(self._build_dir, self._target)]

    # Add the step.
    step_name = 'capture_unittest_coverage'
    self.AddTestStep(shell.ShellCommand, step_name, command)

    # Store the coverage results by the checkout revision.
    src_dir = self.PathJoin(self._build_dir, self._target, 'cov')
    dst_gs_url = WithProperties(
        'gs://syzygy-archive/builds/coverage/%(got_revision)s')
    url = WithProperties(
        'http://syzygy-archive.commondatastorage.googleapis.com/builds/'
           'coverage/%(got_revision)s/index.html')

    command = [self._syzygy_python_exe,
               self.PathJoin(self._script_dir, 'syzygy', 'gsutil_cp_dir.py'),
               src_dir,
               dst_gs_url,]

    desc = 'Archive Coverage Report'
    self._factory.addStep(_UrlStatusCommand,
                          command=command,
                          extra_text=('coverage_report', url),
                          name='archive_coverage',
                          description=desc)

  def AddSmokeTest(self):
    # Smoke-test script path.
    script_path = self.PathJoin(self._repository_root, 'syzygy', 'internal',
                                'build', 'smoke_test.py')

    # We pass in the root build directory to the smoke-test script. It will
    # place its output in <build_dir>/smoke_test, alongside the various
    # configuration sub-directories.
    command = [self._syzygy_python_exe,
               script_path,
               '--verbose',
               '--build-dir',
               self._build_dir]

    self.AddTestStep(shell.ShellCommand, 'smoke_test', command)

  def AddArchival(self):
    """Adds steps to archive the build output for official builds."""
    # Store every file in the "archive" subdir of our build directory."
    archive_dir = self.PathJoin(self._build_dir, self._target, 'archive')
    dst_gs_url = WithProperties(
        'gs://syzygy-archive/builds/official/%(got_revision)s')
    url = WithProperties(
        'http://syzygy-archive.commondatastorage.googleapis.com/index.html?'
            'path=builds/official/%(got_revision)s/')

    command = [self._syzygy_python_exe,
               self.PathJoin(self._script_dir, 'syzygy', 'gsutil_cp_dir.py'),
               archive_dir,
               dst_gs_url,]

    self._factory.addStep(_UrlStatusCommand,
                          command=command,
                          extra_text=('archive', url),
                          name='archive_binaries',
                          description='Archive Binaries')

  def AddUploadSymbols(self):
    """Steps to upload the symbols and symbol-sources for official builds."""
    script_path = self.PathJoin(self._repository_root, 'syzygy', 'internal',
                                'scripts', 'archive_symbols.py')
    # We only upload symbols for the agent DLLs. We use prefix wildcards to
    # (1) account for differing naming conventions across generations of the
    # tools, some prepend a syzygy_ prefix to the DLL name; and (2) to
    # automatically pick up new client DLLs as they are introduced.
    asan_rtl_dll = self.PathJoin(self._build_dir, self._target, '*asan_rtl.dll')
    client_dlls = self.PathJoin(self._build_dir, self._target, '*client.dll')
    command = [self._syzygy_python_exe, script_path, '-s', '-b', asan_rtl_dll,
               client_dlls]
    self._factory.addStep(_UrlStatusCommand,
                          command=command,
                          name='upload_symbols',
                          description='Upload Symbols')
