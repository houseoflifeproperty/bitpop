#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Removes lone *.pyc files which have no corresponding *.py files.

Such files are typically left in the original directory after *.py files are
moved and often create hard-to-debug errors."""

import os
import sys


def main():
  for dirname, dirnames, filenames in os.walk('.', topdown=True):
    # Filter out hidden directories such as '.svn', '.git' etc.
    dirnames[:] = [dn for dn in dirnames if not dn.startswith('.')]

    for filename in filenames:
      if not filename.endswith('.pyc'):
        continue

      pyc_file = os.path.join(dirname, filename)
      py_file = pyc_file[:-3] + 'py'
      if not os.path.isfile(py_file):
        os.remove(pyc_file)
        print 'Removed lone %s file' % pyc_file


if __name__ == '__main__':
  sys.exit(main())
