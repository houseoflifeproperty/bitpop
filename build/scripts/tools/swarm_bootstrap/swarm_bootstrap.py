#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Manages the initial bootstrapping.

Automatically generates the dimensions for the current machine and stores them
in the given file.
"""

import cStringIO
import logging
import optparse
import os
import subprocess
import sys
import urllib2
import zipfile

import start_slave

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def DownloadSwarmBot(swarm_server):
  """Downloads the latest version of swarm_bot code directly from the Swarm
  server.

  It is assumed that this will download a file named slave_machine.py.

  Returns True on success.
  """
  swarm_get_code_url = swarm_server.rstrip('/') + '/get_slave_code'
  try:
    response = urllib2.urlopen(swarm_get_code_url)
  except urllib2.URLError as e:
    logging.error('Unable to download swarm slave code from %s.\n%s',
                  swarm_get_code_url, e)
    return False

  # 'response' doesn't act exactly like a file so we can't pass it directly
  # to the zipfile reader.
  z = zipfile.ZipFile(cStringIO.StringIO(response.read()), 'r')
  try:
    z.extractall()
  finally:
    z.close()
  return True


def CreateStartSlave(filepath):
  """Creates the python scripts that is called to restart the swarm bot slave.

  See src/swarm_bot/slave_machine.py in the swarm server code about why this is
  needed.
  """
  content = (
    'import slave_machine\n'
    'slave_machine.Restart()\n')
  return start_slave.WriteToFile(filepath, content)


def log(line):
  print(line)
  sys.stdout.flush()


def call(cmd):
  log('Running: %s' % ' '.join(cmd))
  return subprocess.call(cmd)


def main():
  # Simplify the code by setting the current directory as the directory
  # containing this file.
  os.chdir(BASE_DIR)

  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option('-d', '--dimensionsfile', default='dimensions.in')
  parser.add_option('-s', '--swarm-server')
  parser.add_option('--no-auto-start', action='store_true',
                    help='Do not setup the swarm bot to auto start on boot.')
  parser.add_option('--no-reboot', action='store_true',
                    help='Do not reboot at the end of the setup.')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Set logging level to DEBUG. Optional. Defaults to '
                    'ERROR level.')
  (options, args) = parser.parse_args()

  if args:
    parser.error('Unexpected argument, %s' % args)
  if not options.swarm_server:
    parser.error('Swarm server is required.')

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.ERROR)

  options.dimensionsfile = os.path.abspath(options.dimensionsfile)

  log('Generating the machine dimensions...')
  if start_slave.GenerateAndWriteDimensions(options.dimensionsfile):
    return 1

  log('Downloading newest swarm_bot code...')
  if not DownloadSwarmBot(options.swarm_server):
    return 1

  slave_machine = os.path.join(BASE_DIR, 'slave_machine.py')
  if not os.path.isfile(slave_machine):
    log('Failed to find %s' % slave_machine)
    return 1

  log('Create start_slave.py script...')
  if not CreateStartSlave(os.path.join(BASE_DIR, 'start_slave.py')):
    return 1

  if not options.no_auto_start:
    log('Setup up swarm script to run on startup...')
    if not start_slave.SetupAutoStartup(
        slave_machine, options.swarm_server, '443', options.dimensionsfile):
      return 1

  if not options.no_reboot:
    log('Rebooting...')
    if sys.platform == 'win32':
      # Run the posix version first. On cygwin 1.5, this is what is necessary.
      result_1 = call(['shutdown', '-r', 'now'])
      # On cygwin 1.7, the windows version has to be used. Run inconditionally,
      # better be safe than sorry.
      result_2 = call(['shutdown', '-r', '-f', '-t', '1'])
      result = not (not result_1 or not result_2)
    else:
      # Run the posix version first. On cygwin 1.5, this is what is necessary.
      result = call(['sudo', 'shutdown', '-r', 'now'])
    if result:
      log('Please reboot the slave manually.')
    return result

  return 0


if __name__ == '__main__':
  sys.exit(main())
