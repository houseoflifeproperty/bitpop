# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the swarm master BuildFactory's.

Based on chromium_factory.py and adds chromium-specific steps."""

from master.factory import build_factory
from master.factory import chromium_factory
from master.factory import swarm_commands

import config


class SwarmTest(object):
  """A small helper class containing any required details to run a
     swarm test.
  """
  def __init__(self, test_name, shards):
    self.test_name = test_name
    self.shards = shards


SWARM_TESTS = [
    # They must be in the reverse order of latency to get results, e.g. the
    # slowest test should be last. The goal here is to take ~60s of actual test
    # run, e.g. the 'RunTest' section in the logs, per shard so that the
    # trade-off of setup time vs latency is reasonable. The overhead is in the
    # range of 10~20s. While it can be lowered, it'll stay in the "few seconds"
    # range due to the sheer size of the executables to map.
    SwarmTest('base_unittests', 1),
    SwarmTest('net_unittests', 3),
    SwarmTest('unit_tests', 4),
    SwarmTest('sync_integration_tests', 4),
    SwarmTest('browser_tests', 10),
]


def SetupSwarmTests(machine, options, swarm_server, ninja, tests):
  """This is a swarm builder."""
  factory_properties = {
    'gclient_env' : {
      'GYP_DEFINES': (
        'test_isolation_mode=hashtable '
        'test_isolation_outdir=' +
        config.Master.swarm_hashtable_server_internal +
        ' fastbuild=1'
      ),
      'GYP_MSVS_VERSION': '2010',
    },
    'compile_env': {
      'ISOLATE_DEBUG': '1',
    },
    'data_dir': config.Master.swarm_hashtable_server_internal,
    'swarm_server': swarm_server
  }
  if ninja:
    factory_properties['gclient_env']['GYP_GENERATORS'] = 'ninja'
    # Build until death.
    options = ['--build-tool=ninja'] + options + ['--', '-k', '0']

  swarm_tests = [s for s in SWARM_TESTS if s.test_name in tests]
  # Accessing machine._target_platform, this function should be a member of
  # SwarmFactory.
  # pylint: disable=W0212
  return machine.SwarmFactory(
      tests=swarm_tests,
      options=options,
      target_platform=machine._target_platform,
      factory_properties=factory_properties)


def SwarmTestBuilder(swarm_server, tests):
  """Create a basic swarm builder that runs tests via swarm."""
  f = build_factory.BuildFactory()

  swarm_command_obj = swarm_commands.SwarmCommands(f)
  swarm_tests = [s for s in SWARM_TESTS if s.test_name in tests]

  # Send the swarm tests to the swarm server.
  swarm_command_obj.AddTriggerSwarmTestStep(
      swarm_server=swarm_server,
      tests=swarm_tests,
      doStepIf=swarm_commands.TestStepHasSwarmProperties)

  # Collect the results
  for swarm_test in swarm_tests:
    swarm_command_obj.AddGetSwarmTestStep(swarm_server, swarm_test.test_name)

  return f


class SwarmFactory(chromium_factory.ChromiumFactory):
  def SwarmFactory(
      self, target_platform, target='Release', clobber=False, tests=None,
      mode=None, options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      gclient_deps=None):
    # Do not pass the tests to the ChromiumFactory, they'll be processed below.
    # Set the slave_type to 'SwarmSlave' to prevent the factory from adding the
    # compile step, so we can add other steps before the compile step.
    f = self.ChromiumFactory(target, clobber, [], mode, 'BuilderTester',
                             options, compile_timeout, build_url, project,
                             factory_properties, gclient_deps)

    swarm_command_obj = swarm_commands.SwarmCommands(
        f,
        target,
        self._build_dir,
        self._target_platform)

    gclient_env = factory_properties.get('gclient_env')
    swarm_server = factory_properties.get('swarm_server',
                                          'http://localhost:9001')
    swarm_server = swarm_server.rstrip('/')

    gyp_defines = gclient_env['GYP_DEFINES']
    if 'test_isolation_mode=hashtable' in gyp_defines:
      test_names = [test.test_name for test in tests]

      swarm_command_obj.AddGenerateResultHashesStep(
          using_ninja='--build-tool=ninja' in (options or []),
          tests=test_names)

      # Send of all the test requests as a single step.
      swarm_command_obj.AddTriggerSwarmTestStep(swarm_server, tests)

      # Each test has its output returned as its own step.
      for test in tests:
        swarm_command_obj.AddGetSwarmTestStep(swarm_server, test.test_name)

    return f
