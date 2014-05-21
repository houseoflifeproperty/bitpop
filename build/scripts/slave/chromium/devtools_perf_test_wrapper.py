#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run Developer Tools perf tests, executed by a buildbot slave.

Runs the run-perf-tests script found in
third_party/WebKit/Tools/Scripts above this script
with 90s timeout because some tests take 60 sec,
with no-results flag because tests have no binary/text results.
with force flag because DevTools has no support on mac and marked
as skipped in WebKit/PerformanceTests/Skipped

Actual tests located at WebKit/PerformanceTests/inspector.
They produce output in format compatible with chromium performance suite.

"""

import optparse
import os
import sys

from common import chromium_utils
from slave import slave_utils


def PerfTest(options):
  """Call run-perf-tests.py, using Python from the tree."""
  build_dir = os.path.abspath(options.build_dir)
  webkit_scripts_dir = chromium_utils.FindUpward(build_dir,
      'third_party', 'WebKit', 'Tools', 'Scripts')
  run_perf_tests = os.path.join(webkit_scripts_dir, 'run-perf-tests')

  command = [run_perf_tests,
             '--time-out-ms=90000',
             '--no-results',
             '--force',
             'inspector',
            ]

  command.append('--' + options.target.lower())

  if options.platform:
    command.extend(['--platform', options.platform])

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e. from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  # Run the the tests
  return slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                                command)


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--build-dir', default='webkit',
      help='path to main build directory (the parent of '
           'the Release or Debug directory)')
  option_parser.add_option('--target', default='release',
      choices=['release', 'debug', 'Release', 'Debug'],
      help='DumpRenderTree build configuration (Release or Debug)')
  option_parser.add_option('--platform',
      help='Platform value passed directly to run-perf-tests.')
  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Unknown argument, try --help')
  return PerfTest(options)


if '__main__' == __name__:
  sys.exit(main())
