# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client specific commands. Based on commands.py"""

import logging

from buildbot.steps import trigger
from buildbot.steps.transfer import FileUpload
from buildbot.process.properties import WithProperties

from master import chromium_step
from master.factory import commands
from master.log_parser import process_log

import config


class NativeClientCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  # pylint: disable=W0212
  # (accessing protected member _NaClBase)
  PERF_BASE_URL = config.Master._NaClBase.perf_base_url

  def __init__(self, factory=None, build_dir=None, target_platform=None):
    commands.FactoryCommands.__init__(self, factory, 'Release', build_dir,
                                      target_platform)

  def AddTrigger(self, trigger_who):
    self._factory.addStep(trigger.Trigger(
        schedulerNames=[trigger_who],
        updateSourceStamp=False,
        waitForFinish=True,
        set_properties={
            'triggered_by_buildername': WithProperties(
                '%(buildername:-None)s'),
            'triggered_by_buildnumber': WithProperties(
                '%(buildnumber:-None)s'),
            'triggered_by_slavename': WithProperties(
                '%(slavename:-None)s'),
            'triggered_by_revision': WithProperties(
                '%(revision:-None)s'),
        }))

  def AddModularBuildStep(self, modular_build_type, timeout=1200):
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='modular_build',
                          description='modular_build',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir='build/native_client/tools/modular-build',
                          command='python build_for_buildbot.py %s' %
                            modular_build_type)

  def AddUploadPerfExpectations(self, factory_properties=None):
    """Adds a step to the factory to upload perf_expectations.json to the
    master.
    """
    perf_id = factory_properties.get('perf_id')
    if not perf_id:
      logging.error("Error: cannot upload perf expectations: perf_id is unset")
      return
    slavesrc = ('native_client/tools/nacl_perf_expectations/'
                'nacl_perf_expectations.json')
    masterdest = ('../../scripts/master/log_parser/perf_expectations/%s.json' %
                  perf_id)
    self._factory.addStep(FileUpload(slavesrc=slavesrc,
                                     masterdest=masterdest))

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
    if 'test_name' not in factory_properties:
      test_class = chromium_step.AnnotatedCommand
    else:
      test_name = factory_properties.get('test_name')
      test_class = self.GetPerfStepClass(
          factory_properties, test_name, process_log.GraphingLogProcessor,
          command_class=chromium_step.AnnotatedCommand)
    if usePython:
      command = [self._python] + command
    self._factory.addStep(test_class,
                          name='annotate',
                          description='annotate',
                          timeout=timeout,
                          haltOnFailure=haltOnFailure,
                          env=env,
                          workdir=workdir,
                          command=command)
