#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Do a revert if a checkout exists."""

import os
import sys

from common import chromium_utils


def main():
  if len(sys.argv) != 3:
    print 'usage: gclient_safe_revert.py build_directory gclient_command'
    return 2

  build_directory = sys.argv[1]
  gclient_command = sys.argv[2]

  if not os.path.exists(build_directory):
    print 'Path %s doesn\'t exist, not running gclient.' % build_directory
    return 0

  if not os.path.isdir(build_directory):
    print 'Path %s isn\'t a directory, not running gclient.' % build_directory
    return 0

  if os.path.isfile(os.path.join(build_directory, 'update.flag')):
    print 'update.flag file found: bot_update has run and checkout is already '
    print 'in a consistent state. No actions will be performed in this step.'
    return 0

  gclient_config = os.path.join(build_directory, '.gclient')
  if not os.path.exists(gclient_config):
    print ('%s doesn\'t exist, not a gclient-controlled checkout.' %
              gclient_config)
    return 0

  # Work around http://crbug.com/280158
  cmd = [gclient_command, 'recurse', '-i', 'sh', '-c',
         'if [ -e .git ]; then git remote update; fi']
  chromium_utils.RunCommand(cmd, cwd=build_directory)

  cmd = [gclient_command, 'revert', '-v', '-v', '-v', '--nohooks', '--upstream']
  return chromium_utils.RunCommand(cmd, cwd=build_directory)


if '__main__' == __name__:
  sys.exit(main())
