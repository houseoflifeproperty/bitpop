#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script acts as the liason between the master and the swarming_client
code.

This helps with master restarts and when swarming_client is updated. It helps
support older versions of the client code, without having to complexify the
master code.
"""

import optparse
import os
import subprocess
import sys

from common import chromium_utils
from common import find_depot_tools  # pylint: disable=W0611

from slave.swarming import swarming_utils

# From depot tools/
import fix_encoding


def v0(client, swarming, isolate_server, tasks, task_prefix, slave_os):
  """Handlers swarm_client/swarm_trigger_step.py.

  Compatible from to the oldest swarm_client code up to r219626.
  """
  cmd = [
    sys.executable,
    os.path.join(client, 'swarm_trigger_step.py'),
    '--swarm-url', swarming,
    '--data-server', isolate_server,
    '--os_image', slave_os,
    '--test-name-prefix', task_prefix,
  ]
  for i in tasks:
    cmd.append('--run_from_hash')
    cmd.extend(i)

  print(' '.join(cmd))
  sys.stdout.flush()
  return subprocess.call(cmd, cwd=client)


def v0_1(
    client, swarming, isolate_server, priority, tasks, task_prefix, slave_os):
  """Handles swarm_client/swarming.py starting r219798."""
  cmd = [
    sys.executable,
    os.path.join(client, 'swarming.py'),
    'trigger',
    '--swarming', swarming,
    '--isolate-server', isolate_server,
    '--os', slave_os,
    '--task-prefix', task_prefix,
    '--priority', str(priority),
  ]

  for i in tasks:
    cmd.append('--task')
    cmd.extend(i)

  # Enable profiling on the -dev server.
  if '-dev' in swarming:
    cmd.append('--profile')

  print(' '.join(cmd))
  sys.stdout.flush()
  return subprocess.call(cmd, cwd=client)


def v0_3(
    client, swarming, isolate_server, priority, tasks, task_prefix, slave_os):
  """Handles swarm_client/swarming.py starting 7c543276f08."""
  ret = 0
  for isolated_hash, test_name, shards, gtest_filter in tasks:
    cmd = [
      sys.executable,
      os.path.join(client, 'swarming.py'),
      'trigger',
      '--swarming', swarming,
      '--isolate-server', isolate_server,
      '--os', slave_os,
      '--priority', str(priority),
      '--shards', str(shards),
      '--task-name', task_prefix + test_name,
      isolated_hash,
    ]
    # Enable profiling on the -dev server.
    if '-dev' in swarming:
      cmd.append('--profile')
    if gtest_filter not in (None, '', '.', '*'):
      cmd.extend(('--env', 'GTEST_FILTER', gtest_filter))
    print(' '.join(cmd))
    sys.stdout.flush()
    ret = max(ret, subprocess.call(cmd, cwd=client))
  return ret


def v0_4(client, swarming, isolate_server, priority, tasks, slave_os):
  """Handles swarm_client/swarming.py starting b39e8cf08c."""
  ret = 0
  for isolated_hash, test_name, shards, gtest_filter in tasks:
    selected_os = swarming_utils.OS_MAPPING[slave_os]
    task_name = '%s/%s/%s' % (test_name, selected_os, isolated_hash)
    cmd = [
      sys.executable,
      os.path.join(client, 'swarming.py'),
      'trigger',
      '--swarming', swarming,
      '--isolate-server', isolate_server,
      '--dimension', 'os', selected_os,
      '--priority', str(priority),
      '--shards', str(shards),
      '--task-name', task_name,
      isolated_hash,
    ]
    # Enable profiling on the -dev server.
    if '-dev' in swarming:
      cmd.append('--profile')
    if gtest_filter not in (None, '', '.', '*'):
      cmd.extend(('--env', 'GTEST_FILTER', gtest_filter))
    print('Triggering %s' % task_name)
    print(' '.join(cmd))
    sys.stdout.flush()
    ret = max(ret, subprocess.call(cmd, cwd=client))
  return ret


def trigger(
    client, swarming, isolate_server, priority, tasks, task_prefix, slave_os):
  """Executes the proper handler based on the code layout and --version support.
  """
  if os.path.isfile(os.path.join(client, 'swarm_get_results.py')):
    # Oh, that's old. This can be removed on 2014-01-01 and replaced on hard
    # failure if swarming.py doesn't exist.
    return v0(client, swarming, isolate_server, tasks, task_prefix, slave_os)

  version = swarming_utils.get_version(client)
  if version < (0, 3):
    return v0_1(
        client, swarming, isolate_server, priority, tasks, task_prefix,
        slave_os)
  if version < (0, 4):
    return v0_3(
        client, swarming, isolate_server, priority, tasks, task_prefix,
        slave_os)
  # It is not using <buildername>-<buildnumber>- anymore.
  return v0_4(client, swarming, isolate_server, priority, tasks, slave_os)


def process_build_properties(options):
  """Converts build properties and factory properties into expected flags."""
  task_prefix = '%s-%s-' % (
      options.build_properties['buildername'],
      options.build_properties['buildnumber'],
  )
  # target_os is not defined when using a normal builder, contrary to a
  # xx_swarm_triggered buildbot<->swarming builder, and it's not needed since
  # the OS match, it's defined in builder/tester configurations.
  slave_os = options.build_properties.get('target_os', sys.platform)
  priority = swarming_utils.build_to_priority(options.build_properties)
  return task_prefix, slave_os, priority


def main():
  """Note: this is solely to run the current master's code and can totally
  differ from the underlying script flags.

  To update these flags:
  - Update the following code to support both the previous flag and the new
    flag.
  - Change scripts/master/factory/swarm_commands.py to pass the new flag.
  - Restart all the masters using swarming.
  - Remove the old flag from this code.
  """
  client = swarming_utils.find_client(os.getcwd())
  if not client:
    print >> sys.stderr, 'Failed to find swarm(ing)_client'
    return 1

  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option('--swarming')
  parser.add_option('--isolate-server')
  parser.add_option(
      '--task', nargs=4, action='append', default=[], dest='tasks')
  chromium_utils.AddPropertiesOptions(parser)
  options, args = parser.parse_args()
  if args:
    parser.error('Unsupported args: %s' % args)

  # Loads the other flags implicitly.
  task_prefix, slave_os, priority = process_build_properties(options)

  return trigger(
      client, options.swarming, options.isolate_server, priority,
      options.tasks, task_prefix, slave_os)


if __name__ == '__main__':
  fix_encoding.fix_encoding()
  sys.exit(main())
