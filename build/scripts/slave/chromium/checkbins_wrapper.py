#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper script for src/tools/checkbins/checkbins.py
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

  build_dir = build_directory.GetBuildOutputDirectory()
  return chromium_utils.RunCommand([
      sys.executable,
      os.path.join('src', 'tools', 'checkbins', 'checkbins.py'),
      os.path.join(build_dir, options.target)
      ])


if '__main__' == __name__:
  sys.exit(main())
