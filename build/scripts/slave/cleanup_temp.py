#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Clean up acculumated cruft, including tmp directory."""

import contextlib
import ctypes
import getpass
import glob
import logging
import os
import socket
import sys
import tempfile
import urllib

from common import chromium_utils
from slave import slave_utils


class FullDriveException(Exception):
  """A disk is almost full."""
  pass


def send_alert(path, left):
  """Sends information about full drive to the breakpad server."""
  url = 'https://chromium-status.appspot.com/breakpad'
  try:
    host = socket.getfqdn()
    params = {
        # args must not be empty.
        'args': '-',
        'stack': 'Only %d bytes left in %s on %s' % (left, path, host),
        'user': getpass.getuser(),
        'exception': 'FullDriveException',
        'host': host,
        'cwd': path,
    }
    request = urllib.urlopen(url, urllib.urlencode(params))
    request.read()
    request.close()
  except IOError, e:
    logging.error(
        'There was a failure while trying to send the stack trace.\n%s' %
            str(e))


def cleanup_directory(directory_to_clean):
  """Cleans up a directory.

  This is a best effort attempt to clean up, since some files will be held
  open for some reason.

  Args:
    directory_to_clean: directory to clean, the directory itself is not deleted.
  """
  try:
    chromium_utils.RemoveDirectory(directory_to_clean)
  except OSError as e:
    print 'Exception removing %s: %s' % (directory_to_clean, e)


@contextlib.contextmanager
def function_logger(header):
  print '%s...' % header.capitalize()
  try:
    yield
  finally:
    print 'Done %s!' % header


def remove_old_isolate_directories(slave_path):
  """Removes all the old isolate directories."""
  with function_logger('removing any old isolate directories'):
    for path in glob.iglob(os.path.join(slave_path, '*', 'build', 'isolate*')):
      print 'Removing %s' % path
      cleanup_directory(path)


def remove_old_isolate_execution_directories_impl_(directory):
  """Removes all the old directories from past isolate executions."""
  for path in glob.iglob(os.path.join(directory, 'run_tha_test*')):
    print 'Removing %s' % path
    cleanup_directory(path)


def remove_old_isolate_execution_directories(slave_path):
  """Removes all the old directories from past isolate executions."""
  with function_logger('removing any old isolate execution directories'):
    remove_old_isolate_execution_directories_impl_(tempfile.gettempdir())
    remove_old_isolate_execution_directories_impl_(slave_path)


def remove_build_dead(slave_path):
  """Removes all the build.dead directories."""
  with function_logger('removing any build.dead directories'):
    for path in glob.iglob(os.path.join(slave_path, '*', 'build.dead')):
      print 'Removing %s' % path
      cleanup_directory(path)


def get_free_space(path):
  """Returns the number of free bytes."""
  if sys.platform == 'win32':
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
    return free_bytes.value
  f = os.statvfs(path)
  return f.f_bfree * f.f_frsize


def check_free_space_path(path, min_free_space=1024*1024*1024):
  """Returns 1 if there isn't enough free space on |path|.

  Defaults to 1gb.
  """
  free_space = get_free_space(path)
  if free_space < min_free_space:
    raise FullDriveException(path, free_space)


def main_win():
  """Main function for Windows platform."""
  with function_logger('removing any Chrome temporary files'):
    slave_utils.RemoveChromeTemporaryFiles()
  if os.path.isdir('e:\\'):
    slave_path = 'e:\\b\\build\\slave'
  else:
    slave_path =  'c:\\b\\build\\slave'
  remove_build_dead(slave_path)
  remove_old_isolate_directories(slave_path)
  remove_old_isolate_execution_directories(slave_path)
  # TODO(maruel): Temporary, add back.
  #cleanup_directory(os.environ['TEMP'])
  check_free_space_path('c:\\')
  if os.path.isdir('e:\\'):
    check_free_space_path('e:\\')
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  # Do not add the following cleanup in slaves_utils.py since we don't want to
  # clean them between each test, as the crash dumps may be processed by
  # 'process build' step.
  with function_logger('removing any crash reports'):
    if 'LOCALAPPDATA' in os.environ:
      crash_reports = os.path.join(
          os.environ['LOCALAPPDATA'], 'Chromium', 'User Data', 'Crash Reports')
      if os.path.isdir(crash_reports):
        for filename in os.listdir(crash_reports):
          filepath = os.path.join(crash_reports, filename)
          if os.path.isfile(filepath):
            os.remove(filepath)
  return 0


def main_mac():
  """Main function for Mac platform."""
  with function_logger('removing any Chrome temporary files'):
    slave_utils.RemoveChromeTemporaryFiles()
  remove_build_dead('/b/build/slave')
  remove_old_isolate_directories('/b/build/slave')
  remove_old_isolate_execution_directories('/b/build/slave')
  # On the Mac, clearing out the entire tmp folder could be problematic,
  # as it might remove files in use by apps not related to the build.
  if os.path.isdir('/b'):
    check_free_space_path('/b')
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  return 0


def main_linux():
  """Main function for linux platform."""
  with function_logger('removing any Chrome temporary files'):
    slave_utils.RemoveChromeTemporaryFiles()
  remove_build_dead('/b/build/slave')
  remove_old_isolate_directories('/b/build/slave')
  remove_old_isolate_execution_directories('/b/build/slave')
  # TODO(maruel): Temporary, add back.
  # cleanup_directory('/tmp')
  if os.path.isdir('/b'):
    check_free_space_path('/b')
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  return 0


def main():
  try:
    if chromium_utils.IsWindows():
      return main_win()
    elif chromium_utils.IsMac():
      return main_mac()
    elif chromium_utils.IsLinux():
      return main_linux()
    else:
      print 'Unknown platform: ' + sys.platform
      return 1
  except FullDriveException, e:
    print >> sys.stderr, 'Not enough free space on %s: %d bytes left' % (
        e.args[0], e.args[1])
    send_alert(e.args[0], e.args[1])


if '__main__' == __name__:
  sys.exit(main())
