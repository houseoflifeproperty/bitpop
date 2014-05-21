# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import omaha_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def win(): return omaha_factory.OmahaFactory('win32')

defaults['category'] = '1windows'

# Main scheduler for the omaha trunk.
#
S('win_trunk', branch='trunk', treeStableTimer=60)

################################################################################
## Release
################################################################################

B('Win7 Release', 'rel', 'compile|windows', 'win_trunk',
  auto_reboot=False, notify_on_missing=True)
F('rel', win().OmahaFactory())

B('Vista Release', 'rel', 'compile|windows', 'win_trunk',
  auto_reboot=False, notify_on_missing=True)
B('XP Release', 'rel', 'compile|windows', 'win_trunk',
  auto_reboot=False, notify_on_missing=True)


################################################################################
## Release
################################################################################

B('Win7 Debug', 'dbg', 'compile|windows', 'win_trunk',
  auto_reboot=False, notify_on_missing=True)
F('dbg', win().OmahaFactory(target='dbg-win'))

B('Vista Debug', 'dbg', 'compile|windows', 'win_trunk',
  auto_reboot=False, notify_on_missing=True)
B('XP Debug', 'dbg', 'compile|windows', 'win_trunk',
  auto_reboot=False, notify_on_missing=True)


def Update(config, active_master, c):
  return helper.Update(c)
