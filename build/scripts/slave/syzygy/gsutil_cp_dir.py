#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to copy a directory tree to Google Storage quickly."""

import optparse
import os
import subprocess
import sys
import time


_GSUTIL = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '../gsutil.bat'))


def MassCopy(src_path, dst_uri, jobs):
  """Copy a directory to Google Storage in parallel.

  Args:
    src_path: path to copy.
    dst_uri: gs://... type uri.
    jobs: maximum concurrent copies.

  Returns:
    Error code for system.
  """
  # Find base path.
  base = os.path.abspath(src_path)

  # Get the list of objects.
  if os.path.isfile(src_path):
    # Handle individual files as a special case (as walk returns []).
    objects = [src_path]
  else:
    objects = []
    for root, _, files in os.walk(src_path):
      objects.extend((os.path.join(root, name) for name in files))
  # Start running copies, limiting how many at once.
  running = []
  try:
    while running or objects:
      while len(running) < jobs and objects:
        o = objects.pop(0)
        ot = os.path.abspath(o)[len(base):]

        # Construct the destination URL, and clean up the slashes to all
        # point forward - the Windows file system produces backslashes.
        dst = '%s%s' % (dst_uri, ot)
        dst = dst.replace(os.path.sep, '/')

        cmd = [_GSUTIL, 'cp', '-t', '-a', 'public-read', o, dst]
        p = subprocess.Popen(cmd, shell=True)
        running.append(p)
      running = [p for p in running if p.poll() is None]
      # Sad having to poll, but at least it behaves nicely in the presence
      # of KeyboardInterrupt.
      time.sleep(0.1)
  except KeyboardInterrupt:
    sys.stderr.write('Interrupt by keyboard, stopping...\n')
    return 2

  return 0


def main(argv):
  usage = ('USAGE: %prog [options] <src> gs://<dst>\n'
           'Copies <src>/xyz... to gs://<dst>/xyz...')
  parser = optparse.OptionParser(usage)
  parser.add_option('-j', '--jobs', type='int', default=20, dest='jobs',
                    help='maximum copies to run in parallel')
  parser.add_option('--message', action='append', default=[], dest='message',
                    help='message to print')
  (options, args) = parser.parse_args(argv)
  if len(args) != 2:
    parser.print_help()
    return 1

  for m in options.message:
    print m

  return MassCopy(src_path=args[0], dst_uri=args[1], jobs=options.jobs)


if __name__ == '__main__':
  sys.exit(main(None))
