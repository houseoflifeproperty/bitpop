#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point for both build and try bots.

To determine which commands to run, the script inspects the given build
properties passed in from buildbot (via command line options).
"""

import optparse
import os
import sys

from common import chromium_utils


SDK_BUILDER_MAP = {
    'linux-sdk-mono32':
        [sys.executable, 'nacl-mono-buildbot.py'],
    'linux-sdk-mono64':
        [sys.executable, 'nacl-mono-buildbot.py'],
    'DEFAULT':
        [sys.executable, 'buildbot_run.py'],
}


def main():
  option_parser = optparse.OptionParser()
  chromium_utils.AddPropertiesOptions(option_parser)
  (options, args) = option_parser.parse_args()

  buildername = options.build_properties.get('buildername', '')
  cmd = SDK_BUILDER_MAP.get(buildername) or SDK_BUILDER_MAP.get('DEFAULT')
  build_tools_dir = chromium_utils.FindUpward(
      os.getcwd(), 'src', 'native_client_sdk', 'src', 'build_tools')
  os.chdir(build_tools_dir)
  # Remove BOTO_CONFIG from the environment -- we want to use the NaCl .boto
  # file that has access to gs://nativeclient-mirror.
  if 'AWS_CREDENTIAL_FILE' in os.environ:
    del os.environ['AWS_CREDENTIAL_FILE']
  if 'BOTO_CONFIG' in os.environ:
    del os.environ['BOTO_CONFIG']
  return chromium_utils.RunCommand(cmd + args)


if __name__ == '__main__':
  sys.exit(main())
