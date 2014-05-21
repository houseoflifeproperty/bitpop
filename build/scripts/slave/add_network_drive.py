#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Maps a network path to a local drive name.
Add the network drive on windows. We run it as a python script so we can
ignore failures that occur if the drive is already setup.
"""

import optparse
import subprocess
import sys


def main():
  """Set the given network path to the given drive id.
  """

  parser = optparse.OptionParser(
    usage='%prog [options]',
    description=sys.modules[__name__].__doc__.splitlines()[0])
  parser.add_option('--drive', help='Drive name to map to.')
  parser.add_option('--network_path', help='Network path to map.')

  (options, args) = parser.parse_args()

  if args:
    parser.error('Please remove unnecessary arguments: ' + '\n'.join(args))
  if not options.drive:
    parser.error('Must specify a drive to map to.')
  if not options.network_path:
    parser.error('Must specify a network path to map.')

  subprocess.call(['net', 'use', options.drive, options.network_path])

  return 0


if __name__ == '__main__':
  sys.exit(main())
