# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

from buildbot.steps import source
from twisted.python import log

from master import chromium_step
from master.factory import commands

import config


def TestStepFilterTriggerSwarm(bStep):
  """Returns True if any swarm step is going to be run by this builder or a
  triggered one.

  This is only useful on the Try Server, where triggering the swarm_triggered
  try builder is conditional on running at least one swarm job there. Nobody
  wants email for an empty job.
  """
  return bool(commands.GetSwarmTests(bStep))


class SwarmingClientGIT(source.Git):
  """Uses the revision specified by use_swarming_client_revision."""

  def start(self):
    """Contrary to source.Source, ignores the branch, source stamp and patch."""
    self.args['workdir'] = self.workdir
    revision = commands.GetProp(self, 'use_swarming_client_revision', None)
    self.startVC(None, revision, None)


class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarming commands to a buildbot factory.

  The builder would be one that only runs swarmed tests.
  """

  def AddUpdateSwarmingClientStep(self):
    """Checks out swarming_client so it can be used at the right revision."""
    # Emulate the path of a src/DEPS checkout, to keep things simpler.
    relpath = 'build/src/tools/swarming_client'
    url = config.Master.git_server_url + '/external/swarming.client'
    self._factory.addStep(
        SwarmingClientGIT,
        repourl=url,
        workdir=relpath)

  def AddSwarmingStep(self, swarming_server, isolate_server):
    """Adds the step to run and get results from Swarming."""
    command = [
      self._python,
      self.PathJoin(self._script_dir, 'swarming', 'swarming_run_shim.py'),
      '--swarming', swarming_server,
      '--isolate-server', isolate_server,
    ]
    command = self.AddBuildProperties(command)

    # Swarm handles the timeouts due to no ouput being produced for 10 minutes,
    # but we don't have access to the output until the whole test is done, which
    # may take more than 10 minutes, so we increase the buildbot timeout.
    timeout = 2 * 60 * 60
    self._factory.addStep(
        chromium_step.AnnotatedCommand,
        name='swarming',
        description='Swarming tests',
        command=command,
        timeout=timeout)

  def AddIsolateTest(self, test_name):
    if not self._target:
      log.msg('No target specified, unable to find isolated files')
      return

    isolated_file = test_name + '.isolated'
    slave_script_path = self.PathJoin(
        self._script_dir, 'swarming', 'isolate_shim.py')

    args = ['run', '--isolated', isolated_file, '--', '--no-cr']
    wrapper_args = [
        '--annotate=gtest',
        '--test-type=%s' % test_name,
        '--pass-build-dir',
        '--pass-target',
        ]

    command = self.GetPythonTestCommand(slave_script_path, arg_list=args,
                                        wrapper_args=wrapper_args)
    self.AddTestStep(chromium_step.AnnotatedCommand,
                     test_name,
                     command)
