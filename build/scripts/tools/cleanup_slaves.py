#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Removes checkouts from try slaves."""

import os
import subprocess
import sys

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def parse_master(master):
  sys.path.append(os.path.join(ROOT_DIR, 'scripts', 'master', 'unittests'))
  import test_env  # pylint: disable=F0401,W0612

  masterpath = os.path.join(ROOT_DIR, 'masters', master)
  os.chdir(masterpath)
  variables = {}
  master = os.path.join(masterpath, 'master.cfg')
  execfile(master, variables)
  return variables['c']


def main():
  """It starts a fake in-process buildbot master just enough to parse
  master.cfg.

  Then it queries all the builders and all the slaves to determine the current
  configuration and process accordingly.
  """
  c = parse_master('master.tryserver.chromium.linux')
  print 'Parsing done.'

  # Create a mapping of slavebuilddir with each slaves connected to it.
  slavebuilddirs = {}
  # Slaves per OS
  all_slaves = {}
  for builder in c['builders']:
    builder_os = builder['name'].split('_', 1)[0]
    if builder_os in ('cros', 'android'):
      builder_os = 'linux'
    slavenames = set(builder['slavenames'])

    all_slaves.setdefault(builder_os, set())
    all_slaves[builder_os] |= slavenames

    slavebuilddir = builder.get('slavebuilddir', builder['name'])
    slavebuilddirs.setdefault(builder_os, {})
    slavebuilddirs[builder_os].setdefault(slavebuilddir, set())
    slavebuilddirs[builder_os][slavebuilddir] |= slavenames

  # Queue of commands to run, per slave.
  queue = {}
  for builder_os, slavebuilddirs in slavebuilddirs.iteritems():
    os_slaves = all_slaves[builder_os]
    for slavebuilddir, slaves in slavebuilddirs.iteritems():
      for slave in os_slaves - slaves:
        queue.setdefault((builder_os, slave), []).append(slavebuilddir)

  print 'Out of %d slaves, %d will be cleaned' % (len(c['slaves']), len(queue))
  commands = []
  for key in sorted(queue):
    slave_os, slavename = key
    dirs = queue[key]
    if slave_os == 'win':
      cmd = 'cmd.exe /c rd /q %s' % ' '.join(
          'e:\\b\\build\\slave\\%s' % s for s in dirs)
    else:
      cmd = 'rm -rf %s' % ' '.join('/b/build/slave/%s' % s for s in dirs)
    commands.append(('ssh', slavename, cmd))

  # TODO(maruel): Use pssh.
  failed = []
  for command in commands:
    print ' '.join(command[1:])
    if subprocess.call(command):
      failed.append(command[1])

  if failed:
    print 'These slaves failed:'
    for i in failed:
      print ' %s' % i
  return 0


if __name__ == '__main__':
  sys.exit(main())
