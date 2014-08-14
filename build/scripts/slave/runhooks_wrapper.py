#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper script for `gclient runhooks`.

This is useful to set slave-dependent gyp defines.
"""

import optparse
import os
import pipes
import sys

from common import chromium_utils


# Path of the scripts/slave/ checkout on the slave, found by looking at the
# current runhooks_wrapper.py script's path's dirname().
SLAVE_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Path of the build/ checkout on the slave, found relative to the
# scripts/slave/ directory.
BUILD_DIR = os.path.dirname(os.path.dirname(SLAVE_SCRIPTS_DIR))


def main():
  parser = optparse.OptionParser(description=__doc__)
  parser.add_option('--use-goma', action='store_true')
  parser.add_option('--goma-dir',
                    default=os.path.join(BUILD_DIR, 'goma'),
                    help='goma directory, only used if --use-goma is passed')
  options, args = parser.parse_args()
  assert not args

  if options.use_goma:
    # Add goma-related GYP_DEFINES if requested. This is done in a slave script
    # because goma_dir is a slave-relative path and is not known to the master.
    gyp_defines = os.environ.get('GYP_DEFINES', '')
    # pipes.quote() is necessary on Windows: http://crbug.com/340918#c7 - 11.
    gyp_defines += ' use_goma=1 gomadir=' + pipes.quote(options.goma_dir)
    os.environ['GYP_DEFINES'] = gyp_defines
    print 'Changed GYP_DEFINES to', os.environ['GYP_DEFINES']

  return chromium_utils.RunCommand([chromium_utils.GetGClientCommand(),
                                    'runhooks'])


if '__main__' == __name__:
  sys.exit(main())
