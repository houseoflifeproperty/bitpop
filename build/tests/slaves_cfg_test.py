#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Ensure that all slaves.cfg files are well formatted and without duplicity.
"""

import os
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_PATH, '..', 'scripts'))

from common import chromium_utils

sys.path.pop(0)

# List of slaves that are allowed to be used more than once.
WHITELIST = ['build1-m6']

def main():
  status = 0
  slaves = {}
  for slave in chromium_utils.GetAllSlaves(fail_hard=True):
    mastername = slave['mastername']
    slavename = chromium_utils.EntryToSlaveName(slave)
    if slave.get('subdir') == 'b':
      print 'Illegal subdir for %s: %s' % (mastername, slavename)
      status = 1
    if slavename and slave.get('hostname') not in WHITELIST:
      slaves.setdefault(slavename, []).append(mastername)
  for slavename, masters in slaves.iteritems():
    if len(masters) > 1:
      print '%s duplicated in masters: %s' % (slavename, ' '.join(masters))
      status = 1
  return status

if __name__ == '__main__':
  sys.exit(main())
