#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script that invokes test-webkitpy."""

import optparse
import os
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--build-dir', help='ignored')

  # Note that --target isn't needed for --lint-test-files, but the
  # RunPythonCommandInBuildDir() will get upset if we don't say something.
  option_parser.add_option('', '--target', default='release',
      help='DumpRenderTree build configuration (Release or Debug)')

  options, _ = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  build_dir = os.path.abspath(options.build_dir)
  webkit_tests_dir = chromium_utils.FindUpward(build_dir,
                                               'third_party', 'WebKit',
                                               'Tools', 'Scripts')
  command = [os.path.join(webkit_tests_dir, 'test-webkitpy')]
  return slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                                command)

if '__main__' == __name__:
  sys.exit(main())
