# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

# CrOS ASan bots below.
defaults['category'] = '4chromeos asan'

_ASAN_SCHEDULER_NAME = 'chromium_src_asan'
helper.Scheduler(_ASAN_SCHEDULER_NAME, branch='src', treeStableTimer=60)

def Builder(dname, sname, flavor, root, board):
  fname = '%s-%s' % (sname, flavor)
  B('%s (%s) Asan' % (dname, sname),
    factory=fname,
    gatekeeper='crosasantest',
    builddir='%s-tot-chromeos-%s-asan' % (flavor, board),
    scheduler=_ASAN_SCHEDULER_NAME,
    notify_on_missing=True)
  F(fname,
    chromeos_factory.CbuildbotFactory(
      buildroot='/b/cbuild/%s' % root,
      pass_revision=True,
      params='%s-tot-asan-informational' % board).get_factory())


Builder('Chromium OS', 'x86', 'chromium', 'shared_external', 'x86-generic')
Builder('Chromium OS', 'amd64', 'chromium', 'shared_external', 'amd64-generic')

def Update(_config, _active_master, c):
  return helper.Update(c)
