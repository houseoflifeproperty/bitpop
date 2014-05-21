#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to check the test_expectations.txt file for errors."""

import optparse
import os
import sys

from common import chromium_utils
from slave import slave_utils


def layout_test(options, args):
  """Parse options and call run_webkit_tests.py, using Python from the tree."""
  build_dir = os.path.abspath(options.build_dir)
  webkit_tests_dir = chromium_utils.FindUpward(build_dir,
                                              'webkit', 'tools', 'layout_tests')
  run_webkit_tests = os.path.join(webkit_tests_dir, 'run_webkit_tests.py')
  command = [run_webkit_tests, '--lint-test-files', '--chromium']

  return slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                                command)

def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--build-dir', default='webkit',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')

  # Note that --target isn't needed for --lint-test-files, but the
  # RunPythonCommandInBuildDir() will get upset if we don't say something.
  option_parser.add_option('', '--target', default='release',
      help='DumpRenderTree build configuration (Release or Debug)')

  options, args = option_parser.parse_args()
  return layout_test(options, args)

if '__main__' == __name__:
  sys.exit(main())
