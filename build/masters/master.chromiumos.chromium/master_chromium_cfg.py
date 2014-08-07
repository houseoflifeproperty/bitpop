# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

defaults['category'] = '2chromium'

# TODO(petermayo): Make this use chrome CROS Manifest too.

_CHROMIUM_SCHEDULER_NAME = 'chromium_cros'
S(name=_CHROMIUM_SCHEDULER_NAME, branch='src', treeStableTimer=60)

def Builder(dname, sname, flavor, root, board):
  fname = '%s-%s' % (sname, flavor)
  B('%s (%s)' % (dname, flavor),
    factory=fname,
    gatekeeper='pfq',
    builddir='%s-tot-chromeos-%s' % (flavor, sname),
    scheduler=_CHROMIUM_SCHEDULER_NAME,
    notify_on_missing=True)
  F(fname,
    chromeos_factory.CbuildbotFactory(
      buildroot='/b/cbuild/%s' % root,
      pass_revision=True,
      params='%s-tot-chrome-pfq-informational' % board).get_factory())


Builder('X86', 'x86', 'chromium', 'shared_external', 'x86-generic')
Builder('AMD64', 'amd64', 'chromium', 'shared_external', 'amd64-generic')
Builder('Daisy', 'daisy', 'chromium', 'shared_external', 'daisy')


def Update(_config, _active_master, c):
  return helper.Update(c)
