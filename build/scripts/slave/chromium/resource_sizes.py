#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to extract size information from a Chromium build, executed by
   Buildbot.
"""

import os
import stat
import sys

def get_size(filename):
  return os.stat(filename)[stat.ST_SIZE]

def main():
  """Print the size of files specified to it as loose args."""
  for f in sys.argv[1:]:
    print "*RESULT ResourceSizes: %s size= %s bytes" % (
        os.path.basename(f), get_size(f))
  return 0

if '__main__' == __name__:
  sys.exit(main())
