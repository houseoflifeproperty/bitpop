# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot master utility functions.
"""

import json
import errno
import logging
import os
import sys
import time

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BUILD_DIR, 'scripts'))

from tools import mastermap
from common import find_depot_tools  # pylint: disable=W0611
import subprocess2


def sublists(superlist, n):
  """Breaks a list into list of sublists, each of length no more than n."""
  result = []
  for cut in range(0, len(superlist), n):
    result.append(superlist[cut:cut + n])
  return result


def pid_exists(pid):
  """Returns True if there is a process in the system with given |pid|."""
  try:
    os.kill(pid, 0)
  except OSError as error:
    if error.errno == errno.EPERM:
      return True
    elif error.errno == errno.ESRCH:
      return False
    raise
  return True


def is_master_alive(master, path):
  """Reads master's *.pid file and checks for corresponding PID in the system.
  If there is no such process, removes stale *.pid file and returns False.

  Returns:
    True - *.pid file exists and corresponding process is running.
    False - *.pid file doesn't exist or there is no such process.
  """
  pid_path = os.path.join(path, 'twistd.pid')
  contents = None
  try:
    with open(pid_path) as f:
      contents = f.read()
    if pid_exists(int(contents.strip())):
      return True
    logging.warning('Ghost twistd.pid for %s, removing it', master)
  except IOError as error:
    if error.errno == errno.ENOENT:
      return False
    raise
  except ValueError:
    logging.warning('Corrupted twistd.pid for %s, removing it: %r',
                    master, contents)
  remove_file(pid_path)
  return False


def remove_file(path):
  """Deletes file at given |path| if it exists. Does nothing if it's not there
  or can not be deleted."""
  try:
    os.remove(path)
  except OSError:
    pass


def start_master(master, path, dry_run=False):
  """Asynchronously starts the |master| at given |path|.
  If |dry_run| is True, will start the master in a limited mode suitable only
  for integration testing purposes.

  Returns:
    True - the master was successfully started.
    False - the master failed to start, details are in the log.
  """
  try:
    env = os.environ.copy()
    if dry_run:
      # Ask ChromiumGitPoller not to pull git repos.
      env['NO_REVISION_AUDIT'] = '0'
      env['POLLER_DRY_RUN'] = '1'
    subprocess2.check_output(
        ['make', 'start'], timeout=120, cwd=path, env=env,
        stderr=subprocess2.STDOUT)
  except subprocess2.CalledProcessError as e:
    logging.error('Error: cannot start %s' % master)
    print e
    return False
  return True


def stop_master(master, path, force=False):
  """Issues 'stop' command and waits for master to terminate. If |force| is True
  will try to kill master process if it fails to terminate in time by itself.

  Returns:
    True - master was stopped, killed or wasn't running.
    False - master is still running.
  """
  if terminate_master(master, path, 'stop', timeout=10):
    return True
  if not force:
    logging.warning('Master %s failed to stop in time', master)
    return False
  logging.warning('Master %s failed to stop in time, killing it', master)
  if terminate_master(master, path, 'kill', timeout=2):
    return True
  logging.warning('Master %s is still running', master)
  return False


def terminate_master(master, path, command, timeout=10):
  """Executes 'make |command|' and waits for master to stop running or until
  |timeout| seconds pass.

  Returns:
    True - the master was terminated or wasn't running.
    False - the command failed, or master failed to terminate in time.
  """
  if not is_master_alive(master, path):
    return True
  try:
    env = os.environ.copy()
    env['NO_REVISION_AUDIT'] = '0'
    subprocess2.check_output(
        ['make', command], timeout=5, cwd=path, env=env,
        stderr=subprocess2.STDOUT)
  except subprocess2.CalledProcessError as e:
    if not is_master_alive(master, path):
      return True
    logging.warning('Master %s was not terminated: \'make %s\' failed: %s',
                    master, command, e)
    return False
  return wait_for_termination(master, path, timeout=timeout)


def wait_for_termination(master, path, timeout=10):
  """Waits for master to finish running and cleans up pid file.
  Waits for at most |timeout| seconds.

  Returns:
    True - master has stopped or wasn't running.
    False - master failed to terminate in time.
  """
  started = time.time()
  while True:
    now = time.time()
    if now > started + timeout:
      break
    if not is_master_alive(master, path):
      logging.info('Master %s stopped in %.1f sec.', master, now - started)
      return True
    time.sleep(0.1)
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
      return ''.join(lines[max(i-15, 0):i+j])
    except ValueError:
      pass
  return False


def json_probe(sensitive, allports):
  """Looks through the port range and finds a master listening.
  sensitive: Indicates whether partial success should be reported.

  Returns (port, name) or None.
  """
  procs = {}
  for ports in sublists(allports, 30):
    for port in ports:
      # urllib2 does not play nicely with threading. Using curl lets us avoid
      # the GIL.
      procs[port] = subprocess2.Popen(
          ['curl', '-fs', '-m2', 'http://localhost:%d/json/project' % port],
          stdin=subprocess2.VOID,
          stdout=subprocess2.PIPE,
          stderr=subprocess2.VOID)
    for port in ports:
      stdout, _ = procs[port].communicate()
      if procs[port].returncode != 0:
        continue
      try:
        data = json.loads(stdout) or {}
        if not data or (not 'projectName' in data and not 'title' in data):
          logging.debug('Didn\'t get valid data from port %d' % port)
          if sensitive:
            return (port, None)
          continue
        name = data.get('projectName', data.get('title'))
        return (port, name)
      except ValueError:
        logging.warning('Didn\'t get valid data from port %d' % port)
        # presume this is some other type of server
        #  E.g. X20 on a dev workstation.
        continue

  return None


def wait_for_start(master, name, path, ports):
  """Waits for ~10s for the masters to open its web server."""
  logging.info("Waiting for master %s on ports %s" % (name, ports))
  for i in range(100):
    result = json_probe(False, ports)
    if result is None:
      exception = search_for_exceptions(path)
      if exception:
        return exception
      time.sleep(0.1)
      continue
    (port, got_name) = result
    if got_name != name:
      return 'Wrong %s name, expected %s, got %s on port %d' % (
          master, name, got_name, port)
    logging.info("Found master %s on port %s, iteration %d" % (name, port, i))
    # The server is now answering /json requests. Check that the log file
    # doesn't have any other exceptions just in case there was some other
    # unexpected error.
    return search_for_exceptions(path)

  return 'Didn\'t find open port for %s' % master


def check_for_no_masters():
  ports = range(8000, 8099) + range(8200, 8299) + range(9000, 9099)
  ports = [x for x in ports if x not in mastermap.PORT_BLACKLIST]
  result = json_probe(True, ports)
  if result is None:
    return True
  if result[1] is None:
    logging.error('Something is listening on port %d' % result[0])
    return False
  logging.error('Found unexpected master %s on port %d' %
                (result[1], result[0]))
  return False
