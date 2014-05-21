#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point for the dartium buildbots.

This script is called from buildbot and reports results using the buildbot
annotation scheme.
"""

import os
import sys

from common import chromium_utils

def main():
  builder_name = os.getenv('BUILDBOT_BUILDERNAME', default='')
  is_release_bot = builder_name.startswith('release')
  script = ''
  if is_release_bot:
    script = 'src/dartium_tools/buildbot_release_annotated_steps.py'
  else:
    script = 'src/dartium_tools/buildbot_annotated_steps.py'

  return chromium_utils.RunCommand([sys.executable, script])

if __name__ == '__main__':
  sys.exit(main())
