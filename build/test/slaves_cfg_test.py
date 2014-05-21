#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Ensure that all slaves.cfg files are well formatted and without duplicity.
"""

import os
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_PATH, '..', 'scripts'))

from common import chromium_utils

# List of slaves that are allowed to be used more than once.
WHITELIST = ['build1-m6']

def main():
  status = 0
  slaves = {}
  for master in chromium_utils.ListMasters(cue='slaves.cfg'):
    masterbase = os.path.basename(master)
    master_slaves = {}
    execfile(os.path.join(master, 'slaves.cfg'), master_slaves)
    for slave in master_slaves.get('slaves', []):
      hostname = slave.get('hostname', None)
      if hostname and hostname not in WHITELIST:
        masters = slaves.get(hostname, [])
        masters.append(masterbase)
        slaves[hostname] = masters
        if len(masters) > 1:
          print '%s duplicated in masters: %s' % (hostname, ' '.join(masters))
          status = 1
  return status

if __name__ == '__main__':
  sys.exit(main())
