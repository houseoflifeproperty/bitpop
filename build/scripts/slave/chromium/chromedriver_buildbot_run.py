#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point for the ChromeDriver buildbots.

This script is called from buildbot and reports results using the buildbot
annotation scheme.
"""

import optparse
import sys

from common import chromium_utils


def main():
  parser = optparse.OptionParser()
  chromium_utils.AddPropertiesOptions(parser)
  options, _ = parser.parse_args()

  return chromium_utils.RunCommand(
      [sys.executable,
       '../../../scripts/slave/runtest.py',
       '--run-python-script',
       'src/chrome/test/chromedriver/run_buildbot_steps.py',
       '--revision',
       options.build_properties.get('got_revision'),
      ])


if __name__ == '__main__':
  sys.exit(main())
