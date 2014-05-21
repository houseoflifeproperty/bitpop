# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')


################################################################################
## Release
################################################################################

defaults['category'] = '2windows'

# Archive location
builddir = 'cr-win-rel-git'
rel_archive = master_config.GetArchiveUrl('ChromiumGIT',
                                          'Win Builder (git)',
                                          builddir,
                                          'win32')

#
# Main debug scheduler for src/
#
S('win_rel', branch='master', treeStableTimer=60)

#
# Triggerable scheduler for the rel builder
#
T('win_rel_trigger')

#
# Win Rel Builder
#
B('Win Builder (git)', 'rel', 'compile|windows', 'win_rel', builddir=builddir,
  auto_reboot=False)
F('rel', win().ChromiumGITFactory(
    slave_type='Builder',
    project='all.sln;chromium_builder_tests',
    factory_properties={'trigger': 'win_rel_trigger'}))

#
# Win Rel testers
#
B('XP Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger')
F('rel_unit_1', win().ChromiumGITFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['browser_tests',
           'cacheinvalidation',
           'courgette',
           'crypto',
           'googleurl',
           'gpu',
           'installer',
           'jingle',
           'media',
           'ppapi_unittests',
           'printing',
           'remoting',
           'sandbox'],
    factory_properties={'process_dumps': True,
                        'browser_total_shards': 3, 'browser_shard_index': 1,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))


def Update(config, active_master, c):
  return helper.Update(c)
