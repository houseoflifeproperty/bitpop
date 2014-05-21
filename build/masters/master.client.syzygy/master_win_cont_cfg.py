# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import syzygy_factory

defaults = { 'category': 'continuous' }

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def win():
  return syzygy_factory.SyzygyFactory('src/build',
                                      target_platform='win32')

#
# Continous build scheduler for Syzygy
#
S('syzygy_cont', branch='trunk', treeStableTimer=60)


#
# Windows continuous Release builder
#
B('Syzygy Release', 'f_syzygy_win_rel', scheduler='syzygy_cont',
  auto_reboot=False)
F('f_syzygy_win_rel', win().SyzygyFactory())


#
# Windows continuous Debug builder
#
B('Syzygy Debug', 'f_syzygy_win_dbg', scheduler='syzygy_cont',
  auto_reboot=False)
F('f_syzygy_win_dbg', win().SyzygyFactory(target='debug'))


#
# Windows continuous code coverage builder
#
B('Syzygy Coverage', 'f_syzygy_win_cov', scheduler='syzygy_cont',
  auto_reboot=False)
F('f_syzygy_win_cov', win().SyzygyCoverageFactory(target='coverage'))


def Update(config, active_master, c):
  return helper.Update(c)
