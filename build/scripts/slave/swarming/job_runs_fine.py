#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs a trivial high priority job on each three major OS to ensure it's still
possible to run a job on each OS.
"""

import Queue
import datetime
import optparse
import os
import shutil
import subprocess
import sys
import threading
import time


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def capture(cmd, **kwargs):
  proc = subprocess.Popen(
      cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, **kwargs)
  out = proc.communicate()[0]
  return out, proc.returncode


def run(
    client_dir, isolated_hash, dimensions, suffix, task_name, isolate_server,
    swarming_server, timeout, channel):
  out = 'An internal error occured'
  code = 1
  duration = -1.
  try:
    cmd = [
      sys.executable,
      'swarming.py',
      'run',
      '--swarming', swarming_server,
      '--isolate-server', isolate_server,
      '--priority', '5',
      '--task-name', '%s-%s' % (task_name, suffix),
      '--deadline', str(timeout),
      '--timeout', str(timeout),
      isolated_hash,
    ]
    for key, value in dimensions.iteritems():
      cmd.extend(('--dimension', key, value))

    start = time.time()
    out, code = capture(cmd, cwd=client_dir)
    duration = time.time() - start
  finally:
    # Only send out if there was a failure.
    channel.put((suffix, out if code else None, duration))


def flatten_dict(d):
  return '/'.join(
      '%s=%s' % (key, value) for key, value in sorted(d.iteritems()))


def main():
  # It is expected that cwd is the build directory.
  cwd = os.getcwd()

  parser = optparse.OptionParser()
  parser.add_option('--canary', action='store_true')
  options, args = parser.parse_args()

  if args:
    parser.error('Unknown args: %s' % args)

  # Testing parameters:
  if options.canary:
    swarming_server = 'https://chromium-swarm-dev.appspot.com'
    isolate_server = 'https://isolateserver-dev.appspot.com'
  else:
    swarming_server = 'https://chromium-swarm.appspot.com'
    isolate_server = 'https://isolateserver.appspot.com'

  dimensions_to_test = (
    {'os': 'Linux'},
    {'os': 'Mac'},
    {'os': 'Windows'},
  )

  # Even under 100% load, a very high priority task should complete within 10
  # minutes.
  timeout = 10*60

  print('Testing servers %s and %s' % (swarming_server, isolate_server))

  code = 0
  client_dir = os.path.join(cwd, 'swarming.client')

  # Copy the files in the build slave directory.
  for item in ('heartbeat.isolate', 'heartbeat.py'):
    shutil.copy(
        os.path.join(ROOT_DIR, 'payload', item),
        os.path.join(cwd, item))

  print('Archiving...')
  start = time.time()
  cmd = [
    sys.executable,
    os.path.join(client_dir, 'isolate.py'),
    'archive',
    '--isolate', 'heartbeat.isolate',
    '--isolated', 'heartbeat.isolated',
    '--isolate-server', isolate_server,
  ]
  isolated_hash = subprocess.check_output(cmd, cwd=cwd).split()[0]
  print('Archiving heartbeat.isolate took %3.1fs' % (time.time() - start))

  now = datetime.datetime.utcnow()
  if options.canary:
    task_name = 'heartbeat-canary-%s' % now.strftime('%Y-%m-%d_%H:%M:%S')
  else:
    task_name = 'heartbeat-%s' % now.strftime('%Y-%m-%d_%H:%M:%S')

  print('Sending tasks named %s' % task_name)
  # Runs the tasks in parallel.
  suffixes_dict = {
    flatten_dict(dimensions): dimensions for dimensions in dimensions_to_test
  }
  assert len(suffixes_dict) == len(dimensions_to_test)
  channel = Queue.Queue(len(suffixes_dict))
  threads = [
    threading.Thread(
      target=run,
      args=(
          client_dir, isolated_hash, dimensions, suffix, task_name,
          isolate_server, swarming_server, timeout, channel))
    for suffix, dimensions in suffixes_dict.iteritems()
  ]
  start = time.time()
  # Add one minute to the deadline to wait for results. This is to take in
  # account potential overhead. In practice, this should be lowered to a few
  # seconds.
  real_timeout = timeout + 60
  deadline = start + real_timeout

  for t in threads:
    t.daemon = True
    t.start()

  while suffixes_dict:
    remaining = deadline - time.time()
    try:
      suffix, out, duration = channel.get(timeout=remaining)
    except Queue.Empty:
      sys.stderr.write(
          'Deadline exceeded to run the tasks within %d seconds.\n' %
          real_timeout)
      sys.stderr.write('Missing:\n')
      for k, v in suffixes_dict.iteritems():
        sys.stderr.write('%s: %s\n' % (k, v))
      return 1

    suffixes_dict.pop(suffix)
    if out:
      # out is only set in case of failure. See finally clause in run().
      sys.stderr.write(
          'Swarming on %s failed (%.2fs):\n' % (suffix, duration))
      sys.stderr.write(out)
      code = 1
    else:
      sys.stdout.write(
          'Swarming on %s success (%.2fs)\n' % (suffix, duration))
      sys.stdout.flush()

  for t in threads:
    t.join()
  return code


if __name__ == '__main__':
  sys.exit(main())
