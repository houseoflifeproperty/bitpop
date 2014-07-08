#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper script for src/chrome/test/mini_installer/test_installer.py.
"""

import optparse
import os
import sys

from slave import build_directory
from common import chromium_utils


def main():
  parser = optparse.OptionParser()
  parser.add_option('--target', help='Release or Debug')
  options, args = parser.parse_args()
  assert not args

  mini_installer_dir = os.path.join('src', 'chrome', 'test', 'mini_installer')
  mini_installer_tests_config = os.path.join(
      mini_installer_dir, 'config', 'config.config')
  return chromium_utils.RunCommand([
      sys.executable,
      os.path.join(mini_installer_dir, 'test_installer.py'),
      mini_installer_tests_config,
      '--build-dir', build_directory.GetBuildOutputDirectory(),
      '--target', options.target,
      '--force-clean',
      ])


if '__main__' == __name__:
  sys.exit(main())
