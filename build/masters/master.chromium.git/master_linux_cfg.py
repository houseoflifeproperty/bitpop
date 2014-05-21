# Copyright (c) 2011 The Chromium Authors. All rights reserved.
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

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '4linux'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumGIT',
                                          'Linux Builder x64 (git)',
                                          'Linux_Builder_x64__git_',
                                          'linux')

#
# Main release scheduler for src/
#
S('linux_rel', branch='master', treeStableTimer=60)

#
# Triggerable scheduler for the rel builder
#
T('linux_rel_trigger')

#
# Linux Rel Builder
#
B('Linux Builder x64 (git)', 'rel', 'compile', 'linux_rel',
  auto_reboot=False)
F('rel', linux().ChromiumGITFactory(
    slave_type='Builder',
    options=['--compiler=goma', 'base_unittests', 'net_unittests'],
    factory_properties={'trigger': 'linux_rel_trigger'}))

#
# Linux Rel testers
#
B('Linux Tests x64 (git)', 'rel_unit', 'testers', 'linux_rel_trigger')
F('rel_unit', linux().ChromiumGITFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['check_deps', 'base', 'net'],
    factory_properties={'generate_gtest_json': True}))

def Update(config, active_master, c):
  return helper.Update(c)
