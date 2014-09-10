# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client specific commands. Based on commands.py"""

from buildbot.process.properties import WithProperties

from master import chromium_step
from master.factory import commands


class NativeClientCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  def __init__(self, factory=None, build_dir=None, target_platform=None):
    commands.FactoryCommands.__init__(self, factory, 'Release', build_dir,
                                      target_platform)

  def AddTrigger(self, trigger_who):
    self._factory.addStep(commands.CreateTriggerStep(
        trigger_name=trigger_who,
        trigger_set_properties={
            'triggered_by_buildername': WithProperties(
                '%(buildername:-None)s'),
            'triggered_by_buildnumber': WithProperties(
                '%(buildnumber:-None)s'),
            'triggered_by_slavename': WithProperties(
                '%(slavename:-None)s'),
            'triggered_by_revision': WithProperties(
                '%(revision:-None)s'),
        },
        waitForFinish=True))

  def AddAnnotatedStep(self, command, timeout=1200,
                       workdir='build/native_client', haltOnFailure=True,
                       factory_properties=None, usePython=False, env=None):
    factory_properties = factory_properties or {}
    env = env or {}
    env = dict(env)
    env['BUILDBOT_TRIGGERED_BY_BUILDERNAME'] = WithProperties(
        '%(triggered_by_buildername:-None)s')
    env['BUILDBOT_TRIGGERED_BY_BUILDNUMBER'] = WithProperties(
        '%(triggered_by_buildnumber:-None)s')
    env['BUILDBOT_TRIGGERED_BY_SLAVENAME'] = WithProperties(
        '%(triggered_by_slavename:-None)s')
    if usePython:
      command = [self._python] + command
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotate',
                          description='annotate',
                          timeout=timeout,
                          haltOnFailure=haltOnFailure,
                          env=env,
                          workdir=workdir,
                          command=command)
