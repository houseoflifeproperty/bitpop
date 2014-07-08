#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This script can daemonize another script. This is usefull in running
background processes from recipes. Lookat chromium_android module for
example.

USAGE:

  daemonizer.py [options] -- <script> [args]

  - options are options to this script. Note, currently there are none!
  - script is the script to daemonize or run in the background
  - args are the arguments that one might want to pass the <script>
"""

# TODO(sivachandra): Enhance this script by enforcing a protocol of
# communication between the parent (this script) and the daemon script.

import os
import subprocess
import sys


def daemonize():
  """This function is based on the Python recipe provided here:
  http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
  """
  # Spawn a detached child process.
  try:
    pid = os.fork()
    if pid > 0:
      # exit first parent
      sys.exit(0)
  except OSError, e:
    sys.stderr.write("fork #1 failed, unable to daemonize: %d (%s)\n" %
                     (e.errno, e.strerror))
    sys.exit(1)

  # decouple from parent environment
  os.chdir("/")
  os.setsid()
  os.umask(0)

  # do second fork
  try:
    pid = os.fork()
    if pid > 0:
      # exit from second parent
      sys.exit(0)
  except OSError, e:
    sys.stderr.write("fork #2 failed, unable to daemonize: %d (%s)\n" %
                     (e.errno, e.strerror))
    sys.exit(1)

  # redirect standard file descriptors
  sys.stdout.flush()
  sys.stderr.flush()
  si = file('/dev/null', 'r')
  so = file('/dev/null', 'a+')
  se = file('/dev/null', 'a+', 0)
  os.dup2(si.fileno(), sys.stdin.fileno())
  os.dup2(so.fileno(), sys.stdout.fileno())
  os.dup2(se.fileno(), sys.stderr.fileno())


def print_usage(err_msg):
  print >> sys.stderr, err_msg
  sys.exit('Usage: daemonizer.py [options] -- arg0 [argN...]')


def main():
  try:
    idx = sys.argv.index('--')
  except ValueError:
    print_usage('Separator -- not found')

  cmd = sys.argv[idx+1:]
  if not cmd:
    print_usage('arg0 not specified for sub command')

  # TODO(sivachandra): When required in the future, use optparse to parse args
  # from sys.argv[:idx]

  daemonize()
  return subprocess.call(cmd)


if __name__ == '__main__':
  sys.exit(main())
