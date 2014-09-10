#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import optparse
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

from common import gtest_utils
from slave import annotation_utils
from slave import slave_utils


MISSING_SHARDS_MSG = r"""Missing results from the following shard(s): %s

It can happen in following cases:
  * Test failed to start (missing *.dll/*.so dependency for example)
  * Test crashed or hung
  * Swarming service experiences problems

Please examine logs to figure out what happened.
"""


def emit_warning(title, log=None):
  print '@@@STEP_WARNINGS@@@'
  print title
  if log:
    slave_utils.WriteLogLines(title, log.split('\n'))


def merge_shard_results(output_dir):
  """Reads JSON test output from all shards and combines them into one.

  Returns dict with merged test output on success or None on failure. Emits
  annotations.
  """
  # summary.json is produced by swarming.py itself. We are mostly interested
  # in the number of shards.
  try:
    with open(os.path.join(output_dir, 'summary.json')) as f:
      summary = json.load(f)
  except (IOError, ValueError):
    emit_warning(
        'summary.json is missing or can not be read',
        'Something is seriously wrong with swarming_client/ or the bot.')
    return None

  # Merge all JSON files together. Keep track of missing shards.
  merged = {
    'all_tests': set(),
    'disabled_tests': set(),
    'global_tags': set(),
    'missing_shards': [],
    'per_iteration_data': [],
  }
  for index, result in enumerate(summary['shards']):
    if result is not None:
      json_data = load_shard_json(output_dir, index)
      if json_data:
        # Set-like fields.
        for key in ('all_tests', 'disabled_tests', 'global_tags'):
          merged[key].update(json_data.get(key), [])

        # 'per_iteration_data' is a list of dicts. Dicts should be merged
        # together, not the 'per_iteration_data' list itself.
        merged['per_iteration_data'] = merge_list_of_dicts(
            merged['per_iteration_data'],
            json_data.get('per_iteration_data', []))
        continue
    merged['missing_shards'].append(index)

  # If some shards are missing, make it known. Continue parsing anyway. Step
  # should be red anyway, since swarming.py return non-zero exit code in that
  # case.
  if merged['missing_shards']:
    as_str = ', '.join(map(str, merged['missing_shards']))
    emit_warning(
        'some shards did not complete: %s' % as_str,
        MISSING_SHARDS_MSG % as_str)
    # Not all tests run, combined JSON summary can not be trusted.
    merged['global_tags'].add('UNRELIABLE_RESULTS')

  # Convert to jsonish dict.
  for key in ('all_tests', 'disabled_tests', 'global_tags'):
    merged[key] = sorted(merged[key])
  return merged


def load_shard_json(output_dir, index):
  """Reads JSON output of a single shard."""
  # 'output.json' is set in swarming/api.py, gtest_task method.
  path = os.path.join(output_dir, str(index), 'output.json')
  try:
    with open(path) as f:
      return json.load(f)
  except (IOError, ValueError):
    print >> sys.stderr, 'Missing or invalid gtest JSON file: %s' % path
    return None


def merge_list_of_dicts(left, right):
  """Merges dicts left[0] with right[0], left[1] with right[1], etc."""
  output = []
  for i in xrange(max(len(left), len(right))):
    left_dict = left[i] if i < len(left) else {}
    right_dict = right[i] if i < len(right) else {}
    merged_dict = left_dict.copy()
    merged_dict.update(right_dict)
    output.append(merged_dict)
  return output


def emit_test_annotations(exit_code, json_data):
  """Emits annotations with logs of failed tests."""
  parser = gtest_utils.GTestJSONParser()
  if json_data:
    parser.ProcessJSONData(json_data)
  annotation_utils.annotate('', exit_code, parser)


def main(args):
  # Split |args| into options for shim and options for swarming.py script.
  if '--' in args:
    index = args.index('--')
    shim_args, swarming_args = args[:index], args[index+1:]
  else:
    shim_args, swarming_args = args, []

  # Parse shim own's options.
  parser = optparse.OptionParser()
  parser.add_option('--swarming-client-dir')
  parser.add_option('--temp-root-dir', default=tempfile.gettempdir())
  parser.add_option('--merged-test-output')
  options, extra_args = parser.parse_args(shim_args)

  # Validate options.
  if extra_args:
    parser.error('Unexpected command line arguments')
  if not options.swarming_client_dir:
    parser.error('--swarming-client-dir is required')

  # Prepare a directory to store JSON files fetched from isolate.
  task_output_dir = tempfile.mkdtemp(
      suffix='_swarming', dir=options.temp_root_dir)

  # Start building the command line for swarming.py.
  args = [
    sys.executable,
    '-u',
    os.path.join(options.swarming_client_dir, 'swarming.py'),
  ]

  # swarming.py run uses '--' to separate args for swarming.py itself and for
  # isolated command. Insert --task-output-dir into section of swarming.py args.
  if '--' in swarming_args:
    idx = swarming_args.index('--')
    args.extend(swarming_args[:idx])
    args.extend(['--task-output-dir', task_output_dir])
    args.extend(swarming_args[idx:])
  else:
    args.extend(swarming_args)
    args.extend(['--task-output-dir', task_output_dir])

  exit_code = 1
  try:
    # Run the real script, regardless of an exit code try to find and parse
    # JSON output files, since exit code may indicate that the isolated task
    # failed, not the swarming.py invocation itself.
    exit_code = subprocess.call(args)

    # Output parsing should not change exit code no matter what, so catch any
    # exceptions and just log them.
    try:
      merged = merge_shard_results(task_output_dir)
      emit_test_annotations(exit_code, merged)
      if options.merged_test_output:
        with open(options.merged_test_output, 'wb') as f:
          json.dump(merged, f, separators=(',', ':'))
    except Exception:
      emit_warning(
          'failed to process gtest output JSON', traceback.format_exc())

  finally:
    shutil.rmtree(task_output_dir, ignore_errors=True)

  return exit_code


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
