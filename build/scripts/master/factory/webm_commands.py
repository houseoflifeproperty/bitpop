# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds webm-specific commands."""

import os

from buildbot.steps import shell
from buildbot.process.properties import WithProperties

from master.factory import commands


class WebMCommands(commands.FactoryCommands):
  """Encapsulates methods to add chromium commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)


  def AddCloneOrFetchRepositoryStep(self, url, checkout_dir="."):
    cmd =  'mkdir -p %s && ' % checkout_dir
    cmd += 'cd %s && ' % checkout_dir
    cmd += 'git init && '
    cmd += 'git fetch origin +refs/*:refs/remotes/origin/*'
    msg = 'Clone/Fetch %s' % checkout_dir
    self._factory.addStep(shell.ShellCommand,
                          command=['bash', '-c', cmd],
                          name=msg,
                          description=msg)


  def AddCheckoutRevisionStep(self, url, rev='%(revision)s', checkout_dir="."):
    cmd =  'git reset --hard && git checkout %s && ' % rev
    cmd += 'git ls-files -o | xargs rm -f'
    msg = 'Checkout'
    self._factory.addStep(shell.ShellCommand,
                          command=['bash', '-c', WithProperties(cmd)],
                          workdir=os.path.join(self._build_dir,checkout_dir),
                          name=msg,
                          description=msg)


  def AddConfigureStep(self, args="", checkout_dir="."):
    cmd =  './configure %s' % args
    msg = 'Configure'
    self._factory.addStep(shell.ShellCommand,
                          command=['bash', '-c', cmd],
                          workdir=os.path.join(self._build_dir,checkout_dir),
                          name=msg,
                          description=msg)


  def AddMakeStep(self, args="", checkout_dir="."):
    cmd =  'make'
    msg = 'Make'
    self._factory.addStep(shell.ShellCommand,
                          command=['bash', '-c', cmd],
                          workdir=os.path.join(self._build_dir,checkout_dir),
                          name=msg,
                          description=msg)


  def AddInstallStep(self, args="", checkout_dir="."):
    cmd =  'make dist'
    msg = 'Make Distribution'
    self._factory.addStep(shell.ShellCommand,
                          command=['bash', '-c', cmd],
                          workdir=os.path.join(self._build_dir,checkout_dir),
                          name=msg,
                          description=msg)
