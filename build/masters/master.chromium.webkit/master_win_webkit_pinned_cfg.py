# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')


################################################################################
## Release
################################################################################

defaults['category'] = '1webkit win deps'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Win Builder (deps)',
                                          'webkit-win-pinned-rel', 'win32')

#
# Main release scheduler for chromium
#
S('s1_chromium_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('s1_chromium_rel_dep', 's1_chromium_rel')

#
# Win Rel Builder
#
B('WebKit Win Builder (deps)', 'f_webkit_win_rel',
  scheduler='s1_chromium_rel', builddir='webkit-win-pinned-rel',
  auto_reboot=False)
F('f_webkit_win_rel', win().ChromiumFactory(
    slave_type='Builder',
    project='all.sln;webkit_builder_win'))

#
# Win Rel WebKit testers
#
B('WebKit XP (deps)', 'f_webkit_rel_tests', scheduler='s1_chromium_rel_dep')
F('f_webkit_rel_tests', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'test_shell',
      'webkit',
      'webkit_lint',
      'webkit_unit',
    ],
    factory_properties={
      'additional_expectations_files': [
        ['webkit', 'tools', 'layout_tests', 'test_expectations.txt' ],
      ],
      'archive_webkit_results': True,
      'generate_gtest_json': True,
      'test_results_server': 'test-results.appspot.com',
    }))

def Update(config, active_master, c):
  return helper.Update(c)
