#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utils for the dart project.
"""

import optparse
import subprocess
import sys

def clobber():
  cmd = [sys.executable,
         './tools/clean_output_directory.py']
  print 'Clobbering %s' % (' '.join(cmd))
  return subprocess.call(cmd)

def main():
  parser = optparse.OptionParser()
  parser.add_option('',
                    '--clobber',
                    default=False,
                    action='store_true',
                    help='Clobber the builder')
  options, args = parser.parse_args()

  # args unused, use.
  args.append('')

  # Determine what to do based on options passed in.
  if options.clobber:
    return clobber()
  else:
    print("Nothing to do")


if '__main__' == __name__ :
  sys.exit(main())
