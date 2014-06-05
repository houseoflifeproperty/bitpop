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


def emit_warning(title, log=None):
  print '@@@STEP_WARNINGS@@@'
  print title
  if log:
    slave_utils.WriteLogLines(title, log.split('\n'))


def process_gtest_json_output(exit_code, output_dir):
  # summary.json is produced by swarming.py itself. We are mostly interested
  # in the number of shards.
  try:
    with open(os.path.join(output_dir, 'summary.json')) as f:
      summary = json.load(f)
  except (IOError, ValueError):
    emit_warning(
        'summary.json is missing or can not be read', traceback.format_exc())
    return

  # For each shard load its JSON output if available and feed it to the parser.
  parser = gtest_utils.GTestJSONParser()
  missing_shards = []
  for index, result in enumerate(summary['shards']):
    if result is not None:
      json_data = load_shard_json(output_dir, index)
      if json_data:
        parser.ProcessJSONData(json_data)
        continue
    missing_shards.append(index)

  # If some shards are missing, make it known. Continue parsing anyway. Step
  # should be red anyway, since swarming.py return non-zero exit code in that
  # case.
  if missing_shards:
    as_str = ' ,'.join(map(str, missing_shards))
    emit_warning(
        'missing results from some shards',
        'Missing results from the following shard(s): %s' % as_str)

  # Emit annotations with a summary of test execution.
  annotation_utils.annotate('', exit_code, parser)


def load_shard_json(output_dir, index):
  try:
    path = os.path.join(output_dir, str(index), 'output.json')
    with open(path) as f:
      return json.load(f)
  except (OSError, ValueError):
    print 'Missing or invalid gtest JSON file: %s' % path
    return None


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
  options, extra_args = parser.parse_args(shim_args)

  # Validate options.
  if extra_args:
    parser.error('Unexpected command line arguments')
  if not options.swarming_client_dir:
    parser.error('--swarming-client-dir is required')

  # Prepare a directory to store output JSON files.
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
      process_gtest_json_output(exit_code, task_output_dir)
    except Exception:
      emit_warning(
          'failed to process gtest output JSON', traceback.format_exc())

  finally:
    shutil.rmtree(task_output_dir, ignore_errors=True)

  return exit_code


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
