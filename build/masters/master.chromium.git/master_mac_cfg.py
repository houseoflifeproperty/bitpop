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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '3mac'

# Archive location
builddir = 'cr-mac-rel-git'
rel_archive = master_config.GetArchiveUrl('ChromiumGIT',
                                          'Mac Builder (git)',
                                          builddir,
                                          'mac')

#
# Main debug scheduler for src/
#
S('mac_rel', branch='master', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('mac_rel_trigger')

#
# Mac Rel Builder
#
B('Mac Builder (git)', 'rel', 'compile', 'mac_rel', builddir=builddir,
  auto_reboot=False)
F('rel', mac().ChromiumGITFactory(
    slave_type='Builder',
    options=['--compiler=goma-clang',
             '--',
             '-target', 'chromium_builder_tests'],
    factory_properties={
      'trigger': 'mac_rel_trigger'}))

#
# Mac Rel testers
#
B('Mac10.6 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger')
F('rel_unit_1', mac().ChromiumGITFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['base',
         'browser_tests',
         'cacheinvalidation',
         'crypto',
         'googleurl',
         'gpu',
         'jingle',
         'media',
         'nacl_integration',
         'ppapi_unittests',
         'printing',
         'remoting'],
  factory_properties={'generate_gtest_json': True,
                      'browser_total_shards': 3, 'browser_shard_index': 1,})
)


def Update(config, active_master, c):
  return helper.Update(c)
