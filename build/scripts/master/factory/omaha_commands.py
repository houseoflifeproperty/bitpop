# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

from buildbot.steps import shell

from master.factory import commands


class OmahaCommands(commands.FactoryCommands):
  """Encapsulates methods to add omaha commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None,
               shard_count=1, shard_run=1, shell_flags=None, isolates=False):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    self._omaha_script_dir = self.PathJoin(self._script_dir, 'omaha')
    self._hammer_tool = self.PathJoin(self._omaha_script_dir, 'hammer.py')


  def AddHammer(self, target=None, options=None):
    options = options or []
    cmd = [self._hammer_tool,
           '--target', target]
    cmd.extend(options)

    self.AddTestStep(shell.ShellCommand, 'Hammer', cmd, timeout=3600)
