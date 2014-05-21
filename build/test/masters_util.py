# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot master utility functions.
"""

import json
import errno
import json
import logging
import os
import sys
import time
import urllib

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_PATH, '..', 'scripts'))

from common import find_depot_tools  # pylint: disable=W0611
import subprocess2


def pid_exists(pid):
  try:
    os.kill(pid, 0)
  except OSError, error:
    if error.errno == errno.EPERM:
      return True
    elif error.errno == errno.ESRCH:
      return False
    raise
  return True


def start_master(master, path):
  try:
    subprocess2.check_output(
        ['make', 'start'], timeout=120, cwd=path,
        stderr=subprocess2.STDOUT)
  except subprocess2.CalledProcessError, e:
    logging.error('Error: cannot start %s' % master)
    print e
    return False
  return True


def stop_master(master, path):
  if not os.path.isfile(os.path.join(path, 'twistd.pid')):
    return True
  try:
    subprocess2.check_output(
        ['make', 'stop'], timeout=60, cwd=path,
        stderr=subprocess2.STDOUT)
    for _ in range(100):
      if not os.path.isfile(os.path.join(path, 'twistd.pid')):
        return True
      time.sleep(0.1)
    return False
  except subprocess2.CalledProcessError, e:
    if 'No such process' in e.stdout:
      logging.warning('Flushed ghost twistd.pid for %s' % master)
      os.remove(os.path.join(path, 'twistd.pid'))
      return True
    return False


def search_for_exceptions(path):
  """Looks in twistd.log for an exception.

  Returns True if an exception is found.
  """
  twistd_log = os.path.join(path, 'twistd.log')
  with open(twistd_log) as f:
    lines = f.readlines()
    stripped_lines = [l.strip() for l in lines]
    try:
      i = stripped_lines.index('--- <exception caught here> ---')
      # Found an exception at line 'i'!  Now find line 'j', the number
      # of lines from 'i' where there's a blank line.  If we cannot find
      # a blank line, then we will show up to 10 lines from i.
      try:
        j = stripped_lines[i:-1].index('')
      except ValueError:
        j = 10
      # Print from either 15 lines back from i or the start of the log
      # text to j lines after i.
      print ''.join(lines[max(i-15, 0):i+j])
      return True
    except ValueError:
      pass
  return False


def json_probe(sensitive, ports=None):
  """ Looks through the port range and finds a master listening.
  sensitive: Indicates whether partial success should be reported.

  Returns (port, name) or None.
  """
  default_ports = range(8000, 8099) + range(8200, 8299) + range(9000, 9099)
  ports = ports or default_ports
  for port in ports:
    try:
      data = json.load(
          urllib.urlopen('http://localhost:%d/json/project' % port)) or {}
      if not data or (not 'projectName' in data and not 'title' in data):
        logging.debug('Didn\'t get valid data from port %d' % port)
        if sensitive:
          return (port, None)
        return None
      name = data.get('projectName', data.get('title'))
      return (port, name)
    except ValueError:
      logging.warning('Didn\'t get valid data from port %d' % port)
      # presume this is some other type of server
      #  E.g. X20 on a dev workstation.
      continue
    except IOError:
      logging.debug('Didn\'t get data from port %d' % port)

  return None


def wait_for_start(master, name, path, ports=None):
  """Waits for ~10s for the masters to open its web server."""
  logging.info("Waiting for master %s on ports %s" % (name, ports))
  for _ in range(100):
    result = json_probe(False, ports)
    if result is None:
      if search_for_exceptions(path):
        return False
      time.sleep(0.01)
      continue
    (port, got_name) = result
    if got_name != name:
      logging.error('Wrong %s name, expected %s, got %s on port %d' %
                    (master, name, got_name, port))
      return False
    logging.info("Found master %s on port %s" % (name, port))
    # The server is now answering /json requests. Check that the log file
    # doesn't have any other exceptions just in case there was some other
    # unexpected error.
    return not search_for_exceptions(path)

  logging.error('Didn\'t find open port for %s' % master)
  return False


def check_for_no_masters():
  result = json_probe(True)
  if result is None:
    return True
  if result[1] is None:
    logging.error('Something is listening on port %d' % result[0])
    return False
  logging.error('Found unexpected master %s on port %d' %
                (result[1], result[0]))
  return False
