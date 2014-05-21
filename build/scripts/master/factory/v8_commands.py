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

  # pylint: disable=W0212
  # (accessing protected member V8)
  PERF_BASE_URL = config.Master.V8.perf_base_url

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None,
               shard_count=1, shard_run=1, shell_flags=None, isolates=False):

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
    if self._isolates:
      cmd += ['--isolates', 'on']
    return cmd

  def AddV8GCMole(self):
    cmd = ['lua', '../../../gcmole/gcmole.lua']
    self.AddTestStep(shell.ShellCommand,
                     'GCMole', cmd,
                     timeout=3600,
                     workdir='build/v8/')

  def AddV8Initializers(self):
    binary = 'out/' + self._target + '/d8'
    cmd = ['bash', './tools/check-static-initializers.sh', binary]
    self.AddTestStep(shell.ShellCommand,
                     'Static-Initializers', cmd,
                     workdir='build/v8/')

  def AddV8Testing(self, properties=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand()
    self.AddTestStep(shell.ShellCommand,
                     'Check', cmd,
                     timeout=3600,
                     workdir='build/v8/')

  def AddV8Test262(self, properties=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand()
    cmd += ['--testname', 'test262']
    self.AddTestStep(shell.ShellCommand, 'Test262', cmd,
                     timeout=3600, workdir='build/v8/')

  def AddV8Mozilla(self, properties=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand()
    cmd += ['--testname', 'mozilla']
    self.AddTestStep(shell.ShellCommand, 'Mozilla', cmd,
                     timeout=3600, workdir='build/v8/')

  def AddPresubmitTest(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--testname', 'presubmit']
    self.AddTestStep(shell.ShellCommand, 'Presubmit', cmd,
                     workdir='build/v8/')

  def AddFuzzer(self, properties=None):
    binary = 'out/' + self._target + '/d8'
    cmd = ['bash', './tools/fuzz-harness.sh', binary]
    self.AddTestStep(shell.ShellCommand, 'Fuzz', cmd,
                     workdir='build/v8/')

  def AddLeakTests(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--testname', 'leak']
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

  def AddArchiveBuild(self, mode='dev', show_url=True,
      extra_archive_paths=None):
    """Adds a step to the factory to archive a build."""
    cmd = [self._python, self._v8archive_tool, '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'Archiving', cmd,
                 workdir='build/v8')

  def AddMoveExtracted(self):
    """Adds a step to download and extract a previously archived build."""
    cmd = ('cp -R sconsbuild/release/* v8/.')
    self._factory.addStep(shell.ShellCommand,
                          description='Move extracted to bleeding',
                          timeout=600,
                          workdir='build',
                          command=cmd)
