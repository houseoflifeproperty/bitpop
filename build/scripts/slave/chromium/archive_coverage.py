#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive croc code coverage to the Chromium buildbot webserver.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.

  Example command line:
      python ../../../scripts/slave/chromium/archive_coverage.py
      --target Debug --perf-subdir linux-debug
"""

import optparse
import os
import socket
import subprocess
import sys

from common import archive_utils
from common import chromium_utils

from slave import slave_utils
from slave import build_directory


def MakeSourceWorldReadable(from_dir):
  """Makes the source tree world-readable."""
  for (dirpath, dirnames, filenames) in os.walk(from_dir):
    for node in dirnames + filenames:
      chromium_utils.MakeWorldReadable(os.path.join(dirpath, node))


class ArchiveCoverage(object):
  """Class to copy coverage HTML to the buildbot webserver."""

  def __init__(self, options):
    """Constructor.

    Args:
      options: Command-line option object from optparse.
    """
    self.options = options
    # Do platform-specific config
    if sys.platform in ('win32', 'cygwin'):
      self.is_posix = False

    elif sys.platform.startswith('darwin'):
      self.is_posix = True

    elif sys.platform.startswith('linux'):
      self.is_posix = True
    else:
      print 'Unknown/unsupported platform.'
      sys.exit(1)

    # Extract the build name of this slave (e.g., 'chrome-release') from its
    # configuration file.
    chrome_dir = os.path.abspath(options.build_dir)
    print 'chrome_dir: %s' % chrome_dir
    build_name = slave_utils.SlaveBuildName(chrome_dir)
    print 'build name: %s' % build_name

    # The 'last change:' line MUST appear for the buildbot output-parser to
    # construct the 'view coverage' link.  (See
    # scripts/master/log_parser/archive_command.py)
    wc_dir = os.path.dirname(chrome_dir)
    self.last_change = str(slave_utils.SubversionRevision(wc_dir))
    print 'last change: %s' % self.last_change

    host_name = socket.gethostname()
    print 'host name: %s' % host_name

    archive_config = archive_utils.Config()

    self.archive_host = archive_config.archive_host
    if self.is_posix:
      # Always ssh/scp to the archive host as chrome-bot.
      self.archive_host = 'chrome-bot@' + self.archive_host
    print 'archive host: %s' % self.archive_host

    if options.perf_subdir:
      self.perf_subdir = options.perf_subdir
    else:
      self.perf_subdir = build_name
    if options.build_number:
      self.perf_subdir = os.path.join(self.perf_subdir, options.build_number)
      print 'build number: %s' % options.build_number
    print 'perf subdir: %s' % self.perf_subdir

    self.archive_path = os.path.join(archive_config.www_dir_base, 'coverage',
                                     self.perf_subdir)

  def Upload(self, archive_folder):
    """Does the actual upload.

    Returns:
      0 if successful, or non-zero error code if error.
    """
    from_dir = os.path.join(self.options.build_dir, self.options.target,
                            archive_folder, 'coverage_croc_html')
    if not os.path.exists(from_dir):
      print '%s directory does not exist' % from_dir
      return slave_utils.WARNING_EXIT_CODE

    archive_path = os.path.join(self.archive_path, archive_folder,
                                self.last_change)
    archive_path = os.path.normpath(archive_path)
    print 'archive path: %s' % archive_path

    if self.is_posix:
      MakeSourceWorldReadable(from_dir)

      cmd = ['ssh', self.archive_host, 'mkdir', '-p', archive_path]
      print 'Running: ' + ' '.join(cmd)
      retval = subprocess.call(cmd)
      if retval:
        return retval

      cmd = ['bash', '-c', 'scp -r -p %s/* %s:%s' %
             (from_dir, self.archive_host, archive_path)]
      print 'Running: ' + ' '.join(cmd)
      retval = subprocess.call(cmd)
      if retval:
        return retval

    else:
      # Windows
      cmd = ['xcopy', '/S', '/I', '/Y', from_dir, archive_path]
      print 'Running: ' + ' '.join(cmd)
      retval = subprocess.call(cmd)
      if retval:
        return retval


def Main():
  """Main routine."""
  option_parser = optparse.OptionParser()
  option_parser.add_option('--target',
                           default='Debug',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--perf-subdir',
                           metavar='DIR',
                           help='destination subdirectory under'
                                'coverage')
  option_parser.add_option('--build-number',
                           help='destination subdirectory under perf-subdir')
  options, args = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  if args:
    option_parser.error('Args not supported: %s' % args)

  ac = ArchiveCoverage(options)
  ac.Upload('total_coverage')

  ac = ArchiveCoverage(options)
  ac.Upload('unittests_coverage')

  ac = ArchiveCoverage(options)
  ac.Upload('browsertests_coverage')

  return 0

if '__main__' == __name__:
  sys.exit(Main())
