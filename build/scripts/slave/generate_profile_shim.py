#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A simple trampoline to generate_profile.py in the src/ directory.

generate_profile.py generates a synthetic user profile.
"""

import optparse
import os
import sys

from slave import build_directory
from common import chromium_utils


def main():
  parser = optparse.OptionParser()
  parser.add_option('--build-dir', help='ignored')
  parser.add_option('--target', help='Release or Debug')
  parser.add_option('--profile-type-to-generate')
  options, args = parser.parse_args()

  output_dir = os.path.join(build_directory.GetBuildOutputDirectory(),
                            options.target,
                            'generated_profile')
  cmd = [
      sys.executable,
      os.path.join('src', 'tools', 'perf', 'generate_profile'),
      '-v',
      '--browser=' + options.target.lower(),
      '--profile-type-to-generate=' + options.profile_type_to_generate,
      '--output-dir=' + output_dir,
      ] + args

  return chromium_utils.RunCommand(cmd)


if '__main__' == __name__:
  sys.exit(main())
