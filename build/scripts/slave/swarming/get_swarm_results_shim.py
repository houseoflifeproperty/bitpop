#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Takes in a test name and retrieves all the output that the swarm server
has produced for tests with that name.

This is expected to be called as a build step.
"""

import optparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from common import chromium_utils
from common import find_depot_tools  # pylint: disable=W0611
from common import gtest_utils

from slave import annotation_utils
from slave.swarming import swarming_utils

# From depot_tools/
import fix_encoding
import subprocess2


NO_OUTPUT_FOUND = (
    'No output produced by the test, it may have failed to run.\n'
    'Showing all the output, including swarm specific output.\n'
    '\n')


def gen_shard_output(result, gtest_parser):
  """Returns output for swarm shard."""
  index = result['config_instance_index']
  machine_id = result['machine_id']
  machine_tag = result.get('machine_tag', 'unknown')

  header = (
    '\n'
    '================================================================\n'
    'Begin output from shard index %s (machine tag: %s, id: %s)\n'
    '================================================================\n'
    '\n') % (index, machine_tag, machine_id)

  # If we fail to get output, we should always mark it as an error.
  if result['output']:
    map(gtest_parser.ProcessLine, result['output'].splitlines())
    content = result['output']
  else:
    content = NO_OUTPUT_FOUND

  test_exit_codes = (result['exit_codes'] or '1').split(',')
  test_exit_code = max(int(i) for i in test_exit_codes)
  test_exit_code = test_exit_code or int(not result['output'])

  footer = (
    '\n'
    '================================================================\n'
    'End output from shard index %s (machine tag: %s, id: %s). Return %d\n'
    '================================================================\n'
  ) % (index, machine_tag, machine_id, test_exit_code)

  return header + content + footer, test_exit_code


def v0(client, options, test_name):
  """This code supports all the earliest versions of swarm_client.

  This is before --version was added.
  """
  sys.path.insert(0, client)
  import swarm_get_results  # pylint: disable=F0401

  timeout = swarm_get_results.DEFAULT_SHARD_WAIT_TIME
  test_keys = swarm_get_results.get_test_keys(
      options.swarming, test_name, timeout)
  if not test_keys:
    print >> sys.stderr, 'No test keys to get results with.'
    return 1

  if options.shards == -1:
    options.shards = len(test_keys)
  elif len(test_keys) < options.shards:
    print >> sys.stderr, ('Warning: Test should have %d shards, but only %d '
                          'test keys were found' % (options.shards,
                                                    len(test_keys)))

  gtest_parser = gtest_utils.GTestLogParser()
  exit_code = None
  shards_remaining = range(len(test_keys))
  first_result = True
  for index, result in swarm_get_results.yield_results(
      options.swarming, test_keys, timeout, None):
    assert index == result['config_instance_index']
    if first_result and result['num_config_instances'] != len(test_keys):
      # There are more test_keys than actual shards.
      shards_remaining = shards_remaining[:result['num_config_instances']]
    shards_remaining.remove(index)
    first_result = False
    output, test_exit_code = gen_shard_output(result, gtest_parser)
    print output
    exit_code = max(exit_code, test_exit_code)

  # Print the annotation before the summary so it's easier to find when scolling
  # down.
  annotation_utils.annotate(test_name, exit_code, gtest_parser)
  print('')
  return exit_code


def v0_1(client, options, test_name):
  """Code starting r219798."""
  swarming = os.path.join(client, 'swarming.py')
  cmd = [
    sys.executable,
    swarming,
    'collect',
    '--swarming', options.swarming,
    '--decorate',
    test_name,
  ]
  print('Running: %s' % ' '.join(cmd))
  sys.stdout.flush()
  proc = subprocess2.Popen(cmd, bufsize=0, stdout=subprocess2.PIPE)
  gtest_parser = gtest_utils.GTestLogParser()
  for line in proc.stdout.readlines():
    line = line.rstrip()
    print line
    gtest_parser.ProcessLine(line)

  proc.wait()

  annotation_utils.annotate(test_name, proc.returncode, gtest_parser)
  print('')
  return proc.returncode


def v0_4(client, options, test_name):
  """Handles swarm_client/swarming.py starting b39e8cf08c."""
  swarming = os.path.join(client, 'swarming.py')
  cmd = [
    sys.executable,
    swarming,
    'collect',
    '--swarming', options.swarming,
    '--decorate',
    test_name,
  ]
  print('Running: %s' % ' '.join(cmd))
  sys.stdout.flush()
  proc = subprocess2.Popen(cmd, bufsize=0, stdout=subprocess2.PIPE)
  gtest_parser = gtest_utils.GTestLogParser()
  for line in proc.stdout.readlines():
    line = line.rstrip()
    print line
    gtest_parser.ProcessLine(line)

  proc.wait()

  annotation_utils.annotate(test_name, proc.returncode, gtest_parser)
  print('')
  return proc.returncode


def determine_version_and_run_handler(client, options, test_name):
  """Executes the proper handler based on the code layout and --version
  support.
  """
  old_test_name, new_test_name = process_build_properties(options, test_name)
  if os.path.isfile(os.path.join(client, 'swarm_get_results.py')):
    # Oh, that's old.
    return v0(client, options, old_test_name)
  version = swarming_utils.get_version(client)
  if version < (0, 4):
    return v0_1(client, options, old_test_name)
  return v0_4(client, options, new_test_name)


def process_build_properties(options, name):
  """Converts build properties and factory properties into expected flags."""
  # Pre 0.4.
  old_taskname = '%s-%s-%s' % (
      options.build_properties.get('buildername'),
      options.build_properties.get('buildnumber'),
      name,
  )
  # 0.4+
  # TODO(maruel): This is a bit adhoc. The good way is to set the buildbot
  # properties or completely do this as a wrapping scripts.
  isolated_hash = options.build_properties.get('swarm_hashes', {}).get(name)
  if not isolated_hash:
    print >> sys.stderr, 'Failed to get hash for %s' % name
    sys.exit(1)
  slave_os = options.build_properties.get('target_os', sys.platform)
  new_taskname = '%s/%s/%s' % (
      name,
      # TODO(maruel): This will have to be runtime specified.
      swarming_utils.OS_MAPPING[slave_os],
      isolated_hash)
  return old_taskname, new_taskname


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

  parser = optparse.OptionParser()
  parser.add_option('-u', '--swarming', help='Swarm server')
  parser.add_option(
      '-s', '--shards', type='int', default=-1, help='Number of shards')
  chromium_utils.AddPropertiesOptions(parser)
  (options, args) = parser.parse_args()
  options.swarming = options.swarming.rstrip('/')

  if not args:
    parser.error('Must specify one test name.')
  elif len(args) > 1:
    parser.error('Must specify only one test name.')
  print('Found %s' % client)
  sys.stdout.flush()
  return determine_version_and_run_handler(client, options, args[0])


if __name__ == '__main__':
  fix_encoding.fix_encoding()
  sys.exit(main())
