#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A small maintenance tool to alert maintainers when an exception is caught."""

import getpass
import logging
import optparse
import os
import socket
import subprocess
import sys
import threading
import urllib

base_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(base_path, '..', '..', '..', 'depot_tools'))

import breakpad  # pylint: disable=F0401,W0611

sys.path.append(os.path.join(base_path, '..'))
from common import chromium_utils


def hack_subprocess():
  """subprocess functions may throw exceptions when used in multiple threads.

  See http://bugs.python.org/issue1731717 for more information.
  """
  subprocess._cleanup = lambda: None


def send_log(path, last_lines):
  """Sends the relevant master log to the breakpad server."""
  url = 'https://chromium-status.appspot.com/breakpad'
  logging.warn('Sending crash report')
  try:
    params = {
        # args must not be empty.
        'args': '-',
        'stack': '\n'.join(last_lines),
        'user': getpass.getuser(),
        'exception': last_lines[-1],
        'host': socket.getfqdn(),
        'cwd': path,
    }
    request = urllib.urlopen(url, urllib.urlencode(params))
    request.read()
    request.close()
  except IOError, e:
    logging.error(
        'There was a failure while trying to send the stack trace.\n%s' %
            str(e))


def process(master_path, maxlines):
  """Processes one master's twistd.log."""
  twistdlog = os.path.join(master_path, 'twistd.log')
  if not os.path.isfile(twistdlog):
    logging.info('No twistd.log file')
    return 1
  logging.info('Monitoring')
  proc = subprocess.Popen(
      ['tail', '-F', twistdlog],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      bufsize=0)
  last_lines = []
  flag = False
  line = ''
  proc.poll()
  while proc.returncode is None:
    proc.poll()
    c = proc.stdout.read(1)
    if c == '\r':
      continue
    if c == '\n':
      last_lines.append(line)
      logging.debug(line)
      if len(last_lines) > maxlines:
        last_lines.pop(0)
      if 'exception caught here' in line:
        logging.info('Had an exception')
        flag = True
      elif not line.strip() and flag:
        send_log(master_path, last_lines[:-1])
        flag = False
      line = ''
    else:
      line += c
  return 0


def main(argv):
  hack_subprocess()
  parser = optparse.OptionParser()
  parser.add_option(
      '--maxlines',
      type=int,
      default=40,
      help='Max number of lines to send')
  parser.add_option(
      '--testing',
      action='store_true',
      help='Override to run on non production hardware')
  parser.add_option('-v', '--verbose', action='store_true')
  options, args = parser.parse_args(argv)
  if args:
    parser.error('Following arguments unsupported:' % args)

  if not socket.getfqdn().endswith('.golo.chromium.org'):
    if not options.testing:
      parser.error('Not running on production hardware')
    else:
      print('WARNING: By running this program you agree to send all the data\n'
          'it generates to Google owned servers and grant rights to use it\n'
          'at will.\n'
          'This program is meant to be used by Google employees only.\n'
          'Use at your own risk and peril.\n')

  if options.verbose:
    level = logging.DEBUG
  else:
    level = logging.INFO
  logging.basicConfig(
      level=level,
      format='%(asctime)s %(levelname)-7s %(threadName)-11s %(message)s',
      datefmt='%m/%d %H:%M:%S')

  masters_path = chromium_utils.ListMasters()
  # Starts tail for each master.
  threads = []
  for master_path in masters_path:
    name = os.path.basename(master_path)
    name = (name
        .replace('master.', '')
        .replace('client.', '')
        .replace('experimental', 'experi')
        .replace('chromiumos', 'cros')
        .replace('tryserver', 't')
        .replace('toolchain', 'tlch')
        .replace('chromium', 'c'))
    thread = threading.Thread(
        target=process,
        args=(master_path, options.maxlines),
        name=name)
    thread.daemon = True
    threads.append(thread)
    thread.start()

  for p in threads:
    p.join()
  return 0


if __name__ == '__main__':
  sys.exit(main(None))
