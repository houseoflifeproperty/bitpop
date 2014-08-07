# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

# CrOS perf bots below.
defaults['category'] = '5chromiumos perf'

_PERF_SCHEDULER_NAME = 'chromium_src_perf'
helper.Scheduler(_PERF_SCHEDULER_NAME, branch='src', treeStableTimer=60)

def Builder(sname, flavor, root, board):
  fname = '%s-%s' % (sname, flavor)
  B('Chromium OS (%s) Perf' % sname,
    factory=fname,
    gatekeeper='crosperf',
    builddir='%s-%s-telemetry' % (flavor, board),
    scheduler=_PERF_SCHEDULER_NAME,
    notify_on_missing=True)
  F(fname,
    chromeos_factory.CbuildbotFactory(
      buildroot='/b/cbuild/%s' % root,
      pass_revision=True,
      params='%s-telemetry' % board).get_factory())


Builder('x86', 'chromium', 'shared_external', 'x86-generic')
Builder('amd64', 'chromium', 'shared_external', 'amd64-generic')

def Update(_config, _active_master, c):
  return helper.Update(c)

