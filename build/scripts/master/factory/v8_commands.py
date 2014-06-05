# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

from buildbot.steps import shell

from master.factory import commands
import config


class V8Commands(commands.FactoryCommands):
  """Encapsulates methods to add v8 commands to a buildbot factory."""

  # This is needed to set legacy perf links. Can be removed when fully converted
  # to the perf dashboard (chromium-perf.appspot.com). See
  # scripts/master/factory/commands.py for how this is used.
  PERF_BASE_URL = config.Master.NaClBase.perf_base_url

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None,
               shard_count=1, shard_run=1, shell_flags=None, isolates=False,
               command_prefix=None, test_env=None, test_options=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform, target_arch)

    # Override _script_dir - one below because we run our build inside
    # the bleeding_edge directory.
    self._script_dir = self.PathJoin('..', self._script_dir)

    # Where to point waterfall links for builds and test results.
    self._archive_url = config.Master.archive_url

    # Where the v8 slave scritps are.
    self._v8_script_dir = self.PathJoin(self._script_dir, 'v8')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._arch = target_arch
    self._shard_count = shard_count
    self._shard_run = shard_run
    self._shell_flags = shell_flags
    self._isolates = isolates
    self._command_prefix = command_prefix
    self._test_env = test_env
    self._test_options = test_options or []

    if self._target_platform == 'win32':
      # Override to use the right python
      python_path = self.PathJoin('third_party', 'python_26')
      self._python = self.PathJoin(python_path, 'python_slave')

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin

    self._v8_test_tool = J(self._build_dir, 'tools')

    # Scripts in the v8 scripts dir.
    self._v8archive_tool = J(self._v8_script_dir, 'v8archive.py')
    self._v8testing_tool = J(self._v8_script_dir, 'v8testing.py')

  def GetV8TestingCommand(self):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target]
    if self._arch:
      cmd += ['--arch', self._arch]
    if self._shard_count > 1:
      cmd += ['--shard_count=%s' % self._shard_count,
              '--shard_run=%s' % self._shard_run]
    if self._shell_flags:
      cmd += ['--shell_flags="'+ self._shell_flags +'"']
    if self._command_prefix:
      cmd += ['--command_prefix', self._command_prefix]
    if self._isolates:
      cmd += ['--isolates', 'on']
    return cmd

  def AddV8GCMole(self):
    cmd = ['lua', './tools/gcmole/gcmole.lua']
    env = {
      'CLANG_BIN': (
        self._build_dir + '../../../../../gcmole/bin'
      ),
      'CLANG_PLUGINS': (
        self._build_dir + '../../../../../gcmole'
      ),
    }
    self.AddTestStep(shell.ShellCommand, 'GCMole', cmd,
                     env=env,
                     timeout=3600,
                     workdir='build/v8/')

  def AddV8Initializers(self):
    binary = 'out/' + self._target + '/d8'
    cmd = ['bash', './tools/check-static-initializers.sh', binary]
    self.AddTestStep(shell.ShellCommand, 'Static-Initializers', cmd,
                     workdir='build/v8/')

  def AddV8Test(self, name, step_name, options=None, flaky_tests='dontcare'):
    options = options or []
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand() + self._test_options + options
    if name:
      cmd += ['--testname', name]
    if flaky_tests == 'run' or flaky_tests == 'skip':
      cmd += ['--flaky-tests', flaky_tests]
    self.AddTestStep(shell.ShellCommand, step_name, cmd,
                     timeout=3600,
                     workdir='build/v8/',
                     env=self._test_env)

  def AddV8TestTC(self, name, step_name, options=None):
    """Adds a tree closer step without flaky tests and another step with."""
    self.AddV8Test(name, step_name, options, flaky_tests='skip')
    self.AddV8Test(name, "%s - flaky" % step_name, options, flaky_tests='run')

  def AddPresubmitTest(self):
    cmd = [self._python, self._v8testing_tool, '--testname', 'presubmit']
    self.AddTestStep(shell.ShellCommand, 'Presubmit', cmd, workdir='build/v8/')

  def AddFuzzer(self):
    binary = 'out/' + self._target + '/d8'
    cmd = ['bash', './tools/fuzz-harness.sh', binary]
    self.AddTestStep(shell.ShellCommand, 'Fuzz', cmd, workdir='build/v8/')

  def AddDeoptFuzzer(self):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = [self._python, './tools/run-deopt-fuzzer.py',
           '--mode', self._target, '--progress=verbose', '--buildbot']
    if self._arch:
      cmd += ['--arch', self._arch]
    if self._shard_count > 1:
      cmd += ['--shard_count=%s' % self._shard_count,
              '--shard_run=%s' % self._shard_run]
    if self._shell_flags:
      cmd += ['--shell_flags="'+ self._shell_flags +'"']
    if self._command_prefix:
      cmd += ['--command_prefix', self._command_prefix]
    if self._isolates:
      cmd += ['--isolates']
    cmd += self._test_options
    self.AddTestStep(shell.ShellCommand, 'Deopt Fuzz', cmd,
                     timeout=3600,
                     workdir='build/v8/',
                     env=self._test_env)

  def AddLeakTests(self):
    cmd = [self._python, self._v8testing_tool, '--testname', 'leak']
    env = {
      'PATH': (
        self._build_dir + '../src/third_party/valgrind/linux_x86/bin;'
      ),
      'VALGRIND_LIB': (
        self._build_dir + '../src/third_party/valgrind/linux_x86/lib/valgrind'
      ),
    }
    self.AddTestStep(shell.ShellCommand, 'leak', cmd,
                     env=env,
                     workdir='build/v8/')

  def AddSimpleLeakTest(self):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = ['valgrind', '--leak-check=full', '--show-reachable=yes',
           '--num-callers=20', './out/%s/d8' % self._target, '-e',
           '"print(1+2)"']
    self.AddTestStep(shell.ShellCommand, 'Simple Leak Check', cmd,
                     timeout=300, workdir='build/v8/')

  def AddArchiveBuild(self, mode='dev', show_url=True,
      extra_archive_paths=None):
    """Adds a step to the factory to archive a build."""
    cmd = [self._python, self._v8archive_tool, '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'Archiving', cmd, workdir='build/v8')
