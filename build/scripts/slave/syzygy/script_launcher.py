#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Trampoline script that uses build_directory to infer the build directory
and expands references to it before calling a child script. Any occurrence
of @{BUILD_DIR} is expanded with the path of the build directory.
"""

import re
import subprocess
import sys

from slave import build_directory


def _ParseOptions():
  args = sys.argv[1:]

  if not args:
    raise Exception('Must specify a script to launch.')

  return args


def _ExpandArgs(args):
  """Expands the arguments in the provided list of arguments. Any occurrence of
  @{BUILD_DIR} is replaced with the actual build directory.
  """
  build_dir = build_directory.GetBuildOutputDirectory()
  eargs = [re.sub('@\{BUILD_DIR\}', build_dir, arg) for arg in args]
  return eargs


def main():
  args = _ParseOptions()
  eargs = _ExpandArgs(args)
  return subprocess.call(eargs)


if __name__ == '__main__':
  sys.exit(main())
