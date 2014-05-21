#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Clean up acculumated cruft, including tmp directory."""

import ctypes
import getpass
import glob
import logging
import os
import socket
import sys
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


def safe_rmdir(path):
  """Tries to delete a directory."""
  try:
    os.rmdir(path)
  except OSError:
    pass  # Ignore failures, this is best effort only


def cleanup_directory(directory_to_clean):
  """Cleans up a directory.

  This is a best effort attempt to clean up, since some files will be held
  open for some reason.

  Args:
    directory_to_clean: directory to clean, the directory itself is not deleted.
  """
  removed_file_count = 0
  for root, dirs, files in os.walk(directory_to_clean, topdown=False):
    for name in files:
      try:
        os.remove(os.path.join(root, name))
        removed_file_count = removed_file_count + 1
      except OSError:
        pass  # Ignore failures, this is best effort only
    for name in dirs:
      safe_rmdir(os.path.join(root, name))
    sys.stdout.write('.')
    sys.stdout.flush()
  print '\nRemoved %d files from %s' % (removed_file_count, directory_to_clean)


def remove_build_dead(slave_path):
  """Removes all the build.dead directories."""
  for path in glob.iglob(os.path.join(slave_path, '*', 'build.dead')):
    print 'Removing %s' % path
    cleanup_directory(path)
    safe_rmdir(path)


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
  slave_utils.RemoveChromeTemporaryFiles()
  if os.path.isdir('e:\\'):
    remove_build_dead('e:\\b\\build\\slave')
  else:
    remove_build_dead('c:\\b\\build\\slave')
  # TODO(maruel): Temporary, add back.
  #cleanup_directory(os.environ['TEMP'])
  check_free_space_path('c:\\')
  if os.path.isdir('e:\\'):
    check_free_space_path('e:\\')
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  # Do not add the following cleanup in slaves_utils.py since we don't want to
  # clean them between each test, as the crash dumps may be processed by
  # 'process build' step.
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
  slave_utils.RemoveChromeTemporaryFiles()
  remove_build_dead('/b/build/slave')
  # On the Mac, clearing out the entire tmp folder could be problematic,
  # as it might remove files in use by apps not related to the build.
  if os.path.isdir('/b'):
    check_free_space_path('/b')
  check_free_space_path(os.environ['HOME'])
  check_free_space_path(os.path.dirname(os.path.abspath(__file__)))
  return 0


def main_linux():
  """Main function for linux platform."""
  slave_utils.RemoveChromeTemporaryFiles()
  remove_build_dead('/b/build/slave')
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
