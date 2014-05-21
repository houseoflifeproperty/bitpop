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
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

defaults['category'] = '7win latest'

# Tests that are single-machine shard-safe. For now we only use the sharding
# supervisor for long tests (more than 30 seconds) that are known to be stable.
sharded_tests = [
  'base_unittests',
  'browser_tests',
  'content_browsertests',
  'media_unittests',
]

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Win Builder',
                                          'win-latest-rel', 'win32')

#
# Main release scheduler for webkit
#
S('s7_webkit_builder_rel', branch='trunk', treeStableTimer=60)
S('s7_webkit_rel', branch='trunk', treeStableTimer=60)

# Triggerable scheduler for testers
T('s7_webkit_builder_rel_trigger')


#
# Win Rel Builders
#
B('Win Builder', 'f_win_rel', scheduler='s7_webkit_builder_rel',
  builddir='win-latest-rel', auto_reboot=False)
F('f_win_rel', win().ChromiumWebkitLatestFactory(
    slave_type='Builder',
    project='all.sln;chromium_builder',
    factory_properties={
        'trigger': 's7_webkit_builder_rel_trigger',
        'gclient_env': { 'GYP_DEFINES': 'fastbuild=1' },
    }))

#
# Win Rel testers+builders
#
# TODO: Switch back to trigger, http://crbug.com/102331
B('Win7 Perf', 'f_win_rel_perf', scheduler='s7_webkit_builder_rel')
F('f_win_rel_perf', win().ChromiumWebkitLatestFactory(
    # TODO: undo, http://crbug.com/102331
    #slave_type='Tester',
    #build_url=rel_archive,
    project='all.sln;chromium_builder_perf',
    tests=[
      'dom_perf',
      'dromaeo',
      'page_cycler_database',
      'page_cycler_dhtml',
      'page_cycler_indexeddb',
      'page_cycler_intl1',
      'page_cycler_intl2',
      'page_cycler_morejs',
      'page_cycler_moz',
      'startup',
      'sunspider',
    ],
    factory_properties={'perf_id': 'chromium-rel-win7-webkit',
                        'show_perf_results': True,
                        'start_crash_handler': True,
                        # TODO: Remove, http://crbug.com/102331
                        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'},
                        }))

B('Vista Tests', 'f_win_rel_tests', scheduler='s7_webkit_builder_rel_trigger')
F('f_win_rel_tests', win().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'installer',
      'unit',
    ],
    factory_properties={'perf_id': 'chromium-rel-vista-webkit',
                        'show_perf_results': True,
                        'start_crash_handler': True,
                        'test_results_server': 'test-results.appspot.com',
                        }))

B('Chrome Frame Tests', 'f_cf_rel_tests',
  scheduler='s7_webkit_builder_rel_trigger')
F('f_cf_rel_tests', win().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'chrome_frame_net_tests',
      'chrome_frame_tests',
      'chrome_frame_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

################################################################################
## Debug
################################################################################


#
# Main debug scheduler for webkit
#
S('s7_webkit_builder_dbg', branch='trunk', treeStableTimer=60)
S('s7_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Win Dbg Builder
#
B('Win7 (dbg)', 'f_win_dbg', scheduler='s7_webkit_builder_dbg',
  builddir='win-latest-dbg')
F('f_win_dbg', win().ChromiumWebkitLatestFactory(
    target='Debug',
    project='all.sln;chromium_builder',
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui',
      'unit',
    ],
    factory_properties={
        'sharded_tests': sharded_tests,
        'start_crash_handler': True,
        'generate_gtest_json': True,
        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'}}))

def Update(config, active_master, c):
  return helper.Update(c)
