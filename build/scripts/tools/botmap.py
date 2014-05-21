#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Dumps a list of known slaves, along with their OS and master."""

import os
import sys
path = os.path.join(os.path.dirname(__file__), os.path.pardir)
sys.path.append(path)
from common import chromium_utils


def main():
  slaves = []
  for master in chromium_utils.ListMasters(cue='slaves.cfg'):
    masterbase = os.path.basename(master)
    master_slaves = {}
    execfile(os.path.join(master, 'slaves.cfg'), master_slaves)
    for slave in master_slaves.get('slaves', []):
      slave['master'] = masterbase
    slaves.extend(master_slaves.get('slaves', []))
  for slave in sorted(slaves, cmp=None, key=lambda x : x.get('hostname', '')):
    slavename = slave.get('hostname')
    if not slavename:
      continue
    master = slave.get('master', '?')
    builder = slave.get('builder', '?')
    if builder == []:
      builder = '?'
    osname = slave.get('os', '?')
    if type(builder) is list:
      for b in sorted(builder):
        print '%-30s %-35s %-35s %-10s' % (slavename, master, b, osname)
    else:
      print '%-30s %-35s %-35s %-10s' % (slavename, master, builder, osname)


if __name__ == '__main__':
  main()
