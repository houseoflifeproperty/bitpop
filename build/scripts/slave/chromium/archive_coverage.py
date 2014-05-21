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
      --target Debug --build-dir src/build --perf-subdir linux-debug
"""

import optparse
import os
import socket
import subprocess
import sys

from common import chromium_utils

from slave import slave_utils
import config


class ArchiveCoverage(object):
  """Class to copy coverage HTML to the buildbot webserver."""

  def __init__(self, options, coverage_folder_name):
    """Constructor.

    Args:
      options: Command-line option object from optparse.
    """
    # Do platform-specific config
    if sys.platform in ('win32', 'cygwin'):
      self.is_posix = False
      self.from_dir = os.path.join(options.build_dir, options.target,
                                   'coverage_croc_html')

    elif sys.platform.startswith('darwin'):
      self.is_posix = True
      self.from_dir = os.path.join(os.path.dirname(options.build_dir),
                                   'xcodebuild', options.target,
                                   'coverage_croc_html')

    elif sys.platform.startswith('linux'):
      self.is_posix = True
      self.from_dir = os.path.join(os.path.dirname(options.build_dir),
                                   'out', options.target, # make, not scons
                                   coverage_folder_name,
                                   'coverage_croc_html')

    else:
      print 'Unknown/unsupported platform.'
      sys.exit(1)

    self.from_dir = os.path.normpath(self.from_dir)
    print 'copy from: %s' % self.from_dir

    if not os.path.exists(self.from_dir):
      print '%s directory does not exist' % self.from_dir
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
    self.last_change = str(slave_utils.SubversionRevision(chrome_dir))
    print 'last change: %s' % self.last_change

    host_name = socket.gethostname()
    print 'host name: %s' % host_name

    archive_config = config.Archive()
    if options.internal:
      archive_config.Internal()

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

    # TODO(jrg) use os.path.join here?
    self.archive_path = '%scoverage/%s/%s' % (
        archive_config.www_dir_base, self.perf_subdir, self.last_change)
    # If this is for collecting coverage for unittests, then create
    # a separate path.
    if coverage_folder_name == 'unittests_coverage':
      self.archive_path = os.path.join(self.archive_path, coverage_folder_name)
    self.archive_path = os.path.normpath(self.archive_path)
    print 'archive path: %s' % self.archive_path

  def _MakeSourceWorldReadable(self):
    """Makes the source tree world-readable."""
    for (dirpath, dirnames, filenames) in os.walk(self.from_dir):
      for node in dirnames + filenames:
        chromium_utils.MakeWorldReadable(os.path.join(dirpath, node))

  def Run(self):
    """Does the actual upload.

    Returns:
      0 if successful, or non-zero error code if error.
    """
    if os.path.exists(self.from_dir) and self.is_posix:
      self._MakeSourceWorldReadable()

      cmd = ['ssh', self.archive_host, 'mkdir', '-p', self.archive_path]
      print 'Running: ' + ' '.join(cmd)
      retval = subprocess.call(cmd)
      if retval:
        return retval

      cmd = ['bash', '-c', 'scp -r -p %s/* %s:%s' %
             (self.from_dir, self.archive_host, self.archive_path)]
      print 'Running: ' + ' '.join(cmd)
      retval = subprocess.call(cmd)
      if retval:
        return retval

    else:
      # Windows
      cmd = ['xcopy', '/S', '/I', '/Y', self.from_dir, self.archive_path]
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
  option_parser.add_option('--build-dir',
                           default='chrome',
                           metavar='DIR',
                           help='directory in which build was run '
                                '[default: %default]')
  option_parser.add_option('--perf-subdir',
                           metavar='DIR',
                           help='destination subdirectory under'
                                'coverage')
  option_parser.add_option('--build-number',
                           help='destination subdirectory under perf-subdir')
  option_parser.add_option('--internal', action='store_true',
                           help='specifies if we should use Internal config')
  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Args not supported: %s' % args)
  ac = ArchiveCoverage(options, 'total_coverage')
  ac.Run()

  auc = ArchiveCoverage(options, 'unittests_coverage')
  auc.Run()
  return 0

if '__main__' == __name__:
  sys.exit(Main())
