#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Updates the Android root/default.prop with extra key=value pairs.

Usage: update_default_props.py ro.adb.secure=0 foo=bar
"""

import collections
import os
import sys

def main(argv):
  android_product_out = os.getenv('ANDROID_PRODUCT_OUT')
  if not android_product_out:
    print 'Run Android envsetup + lunch first.'
    return 1

  file_path = os.path.join(android_product_out, 'root', 'default.prop')
  print 'Updating', file_path
  f = open(file_path, 'r+')

  # Read the current properties.
  print 'Current properties'
  props = collections.OrderedDict()
  for line in f:
    if line.startswith('#') or '=' not in line:
      continue
    k, v = line.strip().split('=')
    print k, '=', v
    props[k] = v

  # Update the props with the one passed in the cmdline.
  for arg in argv[1:]:
    k, v = arg.strip().split('=')
    props[k] = v

  # Update the file.
  f.seek(0, 0)
  f.truncate()
  f.write('# This file was updated by the bot script\n')
  f.write('# %s\n' % argv[0])
  print
  print 'New properties'
  for k, v in props.iteritems():
    f.write('%s=%s\n' % (k, v))
    print k, '=', v

  f.close()
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))