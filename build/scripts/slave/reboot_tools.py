# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Reboot the slave machine, unless it is run in a development
envirenment (TESTING_MASTER environment variable is defined).

The reboot is also controlled by reboot_on_step_timeout flag in the
master config.
"""

import os
import subprocess
import sys
import time


def Log(message):
  """Log a message.

  Use the Buildbot/Twisted log facility if it's imported. Otherwise
  assume we are running in a terminal from a command line.
  """
  log_mod = sys.modules.get('twisted.python.log')
  if log_mod:
    log_mod.msg(message)
  else:
    print message


def IssueReboot():
  """Issue reboot command according to platform type."""
  if sys.platform.startswith('win'):
    subprocess.call(['shutdown', '-r', '-f', '-t', '1'])
  elif sys.platform in ('darwin', 'posix', 'linux2'):
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])
  else:
    raise NotImplementedError('Implement IssueReboot function '
                              'for %s' % sys.platform)


def SigTerm(*args):
  """Receive a SIGTERM and do nothing."""
  Log('SigTerm: Received SIGTERM, doing nothing.')


def UpdateSignals():
  """Override the twisted SIGTERM handler with our own.

  Ensure that the signal module is available and do nothing if it is not.
  """
  try:
    import signal
  except ImportError:
    Log('UpdateSignals: Warning: signal module unavailable -- '
        'not installing signal handlers.')
    return
  # Twisted installs a SIGTERM signal handler which tries to shut the system
  # down.  Use our own handler instead.
  Log('UpdateSignals: installed new SIGTERM handler')
  signal.signal(signal.SIGTERM, SigTerm)


def Sleep(desired_sleep):
  """Sleep for |desired_sleep| seconds.

  time.sleep() can return in less time than desired if the process receives
  a signal.  We expect that to happen when the shutdown we run causes the system
  to send a TERM signal to us.  When that happens, we need to ensure we go
  back to sleep for the remainder of the time that's left."""
  actual_sleep = 0
  while True:
    sleep_length = desired_sleep - actual_sleep
    start_time = int(time.time())
    Log('Sleep: Sleeping for %s seconds' % sleep_length)
    time.sleep(sleep_length)
    this_sleep = int(time.time()) - start_time
    Log('Sleep: Actually slept for %s seconds' % actual_sleep)
    if this_sleep < 0:
      Log('Sleep: Error, this_sleep was %d (less than zero)' % actual_sleep)
      break
    actual_sleep += this_sleep
    if actual_sleep >= desired_sleep:
      Log('Sleep: Finished sleeping, returning' % actual_sleep)
      break
    Log('Sleep: Awoke too early, sleeping again')


def ReallyReboot():
  """Repeatedly try to reboot the system.

     In IssueReboot, use subprocess.call() instead of Popen() to ensure that
     run_slave.py doesn't exit at all when it calls Reboot().  This ensures that
     run_slave.py won't exit and trigger any cleanup routines by whatever
     launched run_slave.py.

  Since our strategy depends on Reboot() never returning, raise an exception
  if that should occur to make it clear in logs that an error condition is
  occurring somewhere.
  """
  Log('Reboot: Starting system reboot cycle')
  UpdateSignals()
  i = 0
  try:
    while True:
      Log('Reboot: Reboot cycle %d' % i)
      IssueReboot()
      Sleep(60)
      i += 1
  except:
    Log('Reboot: failed to issue a reboot: %s' % str(sys.exc_info()[0]))
    raise


def Reboot():
  """Reboot the buildbot slave machine.

  This behavior is controlled by the reboot_on_step_timeout flag in
  the active master configuration.
  """
  # This envrionment is defined only when testing the slave on a dev machine.
  is_testing = 'TESTING_MASTER' in os.environ

  should_reboot = False
  try:
    import config_bootstrap
    master = getattr(config_bootstrap.Master, 'active_master', None)
    should_reboot = getattr(master, 'reboot_on_step_timeout', True)
    Log('Reboot: reboot_on_step_timeout = %r (from master_site_config: %r)'
        % (should_reboot, master))
  except:  # pylint: disable=W0702
    Log('Reboot: failed to read master config: %s' % str(sys.exc_info()[0]))
    return

  if should_reboot:
    if not is_testing:
      Log('Reboot: Issuing Reboot...')
      ReallyReboot()
    else:
      Log('Reboot: Testing mode enabled, skipping the actual reboot')
