#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the crash handler executable, used by the buildbot slaves.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  This can only be run on Windows.

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import sys
try:
  # pylint: disable=F0401
  import win32process
except ImportError:
  print >> sys.stderr, 'This script runs on Windows only.'
  sys.exit(1)

from common import chromium_utils
from slave import build_directory

USAGE = '%s [options]' % os.path.basename(sys.argv[0])


def main():
  """Using the target build configuration, run the crash_service.exe
  executable.
  """
  option_parser = optparse.OptionParser(usage=USAGE)

  option_parser.add_option('--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('--build-dir', help='ignored')
  options, args = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  if args:
    option_parser.error('No args are supported')

  build_dir = os.path.abspath(options.build_dir)
  exe_path = os.path.join(build_dir, options.target, 'crash_service.exe')
  if not os.path.exists(exe_path):
    raise chromium_utils.PathNotFound('Unable to find %s' % exe_path)

  # crash_service's window can interfere with interactive ui tests.
  cmd = exe_path + ' --no-window'

  print '\n' + cmd + '\n',

  # We cannot use Popen or os.spawn here because buildbot will wait until
  # the process terminates before going to the next step. Since we want to
  # keep the process alive, we need to explicitly say that we want the
  # process to be detached and that we don't want to inherit handles from
  # the parent process.
  si = win32process.STARTUPINFO()
  details = win32process.CreateProcess(None, cmd, None, None, 0,
                                       win32process.DETACHED_PROCESS, None,
                                       None, si)
  print '\nCreated with process id %d\n' % details[2]
  return 0


if '__main__' == __name__:
  sys.exit(main())
