#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to copy a directory tree to Google Storage quickly."""

import optparse
import os
import subprocess
import sys
import time


class ShellJob(object):
  """A job to run thru the shell."""
  def __init__(self, cmd, retries):
    """Create a job.

    Args:
      cmd: command line to invoke.
      retries: times to re-attempt the command on failure.
    """
    self.cmd = cmd
    self.process = None
    self.retries = retries
    self.times_tried = 0
    self.state = None

  def Run(self):
    """Run or re-run as needed.

    Returns:
      None if still in progress or return code (zero unless retry failed).
    """
    if self.state is not None:
      return self.state
    if self.process is not None:
      retcode = self.process.poll()
      if retcode is None:
        return None
      if retcode == 0:
        self.state = 0
        return 0
      else:
        print 'Command: %s, failed with return code %d, attempt %d of %d' % (
            self.cmd, retcode, self.times_tried, self.retries + 1,
        )
    if self.times_tried <= self.retries:
      self.times_tried += 1
      print self.cmd
      sys.stdout.flush()
      self.process = subprocess.Popen(self.cmd, shell=True)
      return None
    else:
      self.state = -1
    return self.state


def ShellEscape(s):
  """Escape a string to be passed to the shell.
  Args:
    s: String to escape.
  Returns:
    Escaped string.
  """
  return "'" + s.replace("'", "'\\''") + "'"


def MassCopy(src_path, dst_uri, jobs, retries, acl):
  """Copy a directory to Google Storage in parallel.

  Args:
    src_path: path to copy.
    dst_uri: gs://... type uri.
    jobs: maximum concurrent copies.
    retries:  times to re-attempt commands on failure.
    acl: value to pass for gsutil's -a parameter.
  Returns:
    Error code for system.
  """
  # Pick gsutil.
  gsutil = os.environ.get('GSUTIL', 'gsutil')
  if acl:
    acl_arg = '-a%s' % acl
  else:
    acl_arg = ''
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
  total_result = 0
  try:
    while running or objects:
      # Update the running set.
      still_running = []
      for job in running:
        retcode = job.Run()
        if retcode is None:
          still_running.append(job)
        else:
          if retcode != 0:
            # Return the first retcode.
            if total_result == 0:
              total_result = retcode
      running = still_running

      # Start running more if we can.
      while len(running) < jobs and objects:
        o = objects.pop(0)
        ot = os.path.abspath(o)[len(base):]
        cmd = '%s cp %s %s %s' % (
          ShellEscape(gsutil),
          ShellEscape(acl_arg),
          ShellEscape(o),
          ShellEscape(dst_uri + ot))
        running.append(ShellJob(cmd, retries))

      # Sad having to poll, but at least it behaves nicely in the presence
      # of KeyboardInterrupt.
      time.sleep(0.1)
  except KeyboardInterrupt:
    sys.stderr.write('Interrupt by keyboard, stopping...\n')
    return 2

  return total_result


def main(argv):
  usage = ('USAGE: %prog [options] <src> gs://<dst>\n'
           'Copies <src>/xyz... to gs://<dst>/xyz...')
  parser = optparse.OptionParser(usage)
  parser.add_option('-j', '--jobs', type='int', default=20, dest='jobs',
                    help='maximum copies to run in parallel')
  parser.add_option('--message', action='append', default=[], dest='message',
                    help='message to print')
  parser.add_option('-r', '--retries', type='int', default=3,
                    dest='retries', help='times to retry')
  parser.add_option('-a', '--acl', default=None, dest='acl',
                    help='value to pass to for -a argument of gsutil cp')
  (options, args) = parser.parse_args(argv)
  if len(args) != 2:
    parser.print_help()
    return 1

  for m in options.message:
    print m

  return MassCopy(src_path=args[0], dst_uri=args[1],
                  jobs=options.jobs, retries=options.retries, acl=options.acl)


if __name__ == '__main__':
  sys.exit(main(None))
