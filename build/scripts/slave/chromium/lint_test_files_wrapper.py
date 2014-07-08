#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to check the test_expectations.txt file for errors."""

import optparse
import os
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def layout_test(options, args):
  """Parse options and call run-webkit-tests, using Python from the tree."""
  build_dir = os.path.abspath(options.build_dir)
  blink_scripts_dir = chromium_utils.FindUpward(build_dir,
    'third_party', 'WebKit', 'Tools', 'Scripts')
  lint_tests_script = os.path.join(blink_scripts_dir, 'lint-test-expectations')

  return slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                                [lint_tests_script])

def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--build-dir', help='ignored')

  # Note that --target isn't needed for --lint-test-files, but the
  # RunPythonCommandInBuildDir() will get upset if we don't say something.
  option_parser.add_option('', '--target', default='release',
      help='DumpRenderTree build configuration (Release or Debug)')

  options, args = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()
  return layout_test(options, args)

if '__main__' == __name__:
  sys.exit(main())
