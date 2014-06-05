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

def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')
def win_out():
  return chromium_factory.ChromiumFactory('src/out', 'win32')
def win_tester():
  return chromium_factory.ChromiumFactory(
      'src/build', 'win32', nohooks_on_update=True)

# Tests that are single-machine shard-safe.
sharded_tests = [
  'aura_unittests',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cast_unittests',
  'cc_unittests',
  'chrome_elf_unittests',
  'chromedriver_tests',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'device_unittests',
  'events_unittests',
  'gcm_unit_tests',
  'google_apis_unittests',
  'gpu_unittests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  # http://crbug.com/157234
  #'sync_integration_tests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'views_unittests',
  'webkit_compositor_bindings_unittests',
]

################################################################################
## Release
################################################################################

defaults['category'] = '2windows'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWin', 'Win Builder',
                                          'cr-win-rel', 'win32')

# Archive location
rel_x64_archive = master_config.GetArchiveUrl('ChromiumWin', 'Win x64 Builder',
                                              'cr-win-rel-x64', 'win32')

#
# Main debug scheduler for src/
#
S('win_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel builder
#
T('win_rel_trigger')

#
# Win Rel Builder
#
B('Win Builder', 'rel', 'compile|windows', 'win_rel', builddir='cr-win-rel',
  auto_reboot=False, notify_on_missing=True)
F('rel', win().ChromiumFactory(
    slave_type='Builder',
    options=['--compiler=goma'],
    project='all.sln;chromium_builder_tests',
    factory_properties={'trigger': 'win_rel_trigger',
                        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'}}))

#
# Win Rel testers
#
B('XP Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
F('rel_unit_1', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'browser_tests',
      'cacheinvalidation_unittests',
      'cast',
      'cc_unittests',
      'chromedriver_unittests',
      'content_browsertests',
      'courgette_unittests',
      'crypto_unittests',
      'gfx_unittests',
      'gpu',
      'installer',
      'interactive_ui_tests',
      'jingle',
      'media',
      'ppapi_unittests',
      'printing',
      'remoting',
      'sandbox',
      'url_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 1,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('XP Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
F('rel_unit_2', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'ash_unittests',
      'aura',
      'base_unittests',
      'browser_tests',
      'compositor',
      'events',
      'net',
      'telemetry_perf_unittests',
      'telemetry_unittests',
      'views_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 2,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('XP Tests (3)', 'rel_unit_3', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
F('rel_unit_3', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'browser_tests',
      'chrome_elf_unittests',
      'components_unittests',
      'gcm_unit_tests',
      'google_apis_unittests',
      'unit',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 3,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Vista Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
B('Vista Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
B('Vista Tests (3)', 'rel_unit_3', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
B('Win7 Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
B('Win7 Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
B('Win7 Tests (3)', 'rel_unit_3', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)

B('Win7 Sync', 'rel_sync', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
F('rel_sync', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['sync_integration'],
    factory_properties={
      'generate_gtest_json': True,
      'process_dumps': True,
      'sharded_tests': sharded_tests,
      'start_crash_handler': True,
    }))

#
# Triggerable scheduler for the rel builder
#
T('win_x64_rel_trigger')

#
# Win x64 Rel Builder
# Note: These should eventually merge with the build and test targets for
# win_rel above.
#
B('Win x64 Builder', 'rel_x64', 'compile|windows', 'win_rel',
  builddir='cr-win-rel-x64', auto_reboot=False, notify_on_missing=True)
F('rel_x64', win_out().ChromiumFactory(
    compile_timeout=2400,
    slave_type='Builder',
    target='Release_x64',
    options=['--compiler=goma', '--', 'all'],
    factory_properties={
      'trigger': 'win_x64_rel_trigger',
      'gclient_env': {
        'GYP_DEFINES': 'component=shared_library target_arch=x64',
      }}))

B('Win 7 Tests x64 (1)', 'rel_x64_unit_1', 'windows',
  'win_x64_rel_trigger', notify_on_missing=True)
F('rel_x64_unit_1', win_tester().ChromiumFactory(
    slave_type='Tester',
    target='Release_x64',
    build_url=rel_x64_archive,
    tests=[
      'browser_tests',
      'cacheinvalidation_unittests',
      'cast_unittests',
      'cc_unittests',
      'chromedriver_unittests',
      'content_browsertests',
      'courgette_unittests',
      'crypto_unittests',
      'gcm_unit_tests',
      'google_apis_unittests',
      'gpu_unittests',
      'installer_util_unittests',
      'interactive_ui_tests',
      'jingle_unittests',
      'media_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sbox_integration_tests',
      'sbox_unittests',
      'sbox_validation_tests',
      'url_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 1,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Win 7 Tests x64 (2)', 'rel_x64_unit_2', 'windows',
  'win_x64_rel_trigger', notify_on_missing=True)
F('rel_x64_unit_2', win_tester().ChromiumFactory(
    slave_type='Tester',
    target='Release_x64',
    build_url=rel_x64_archive,
    tests=[
      'app_list_unittests',
      'base_unittests',
      'browser_tests',
      'chrome_elf_unittests',
      'net_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 2,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Win 7 Tests x64 (3)', 'rel_x64_unit_3', 'windows',
  'win_x64_rel_trigger', notify_on_missing=True)
F('rel_x64_unit_3', win_tester().ChromiumFactory(
    slave_type='Tester',
    target='Release_x64',
    build_url=rel_x64_archive,
    tests=[
      'browser_tests',
      'components_unittests',
      'content_unittests',
      'gfx_unittests',
      'ipc_tests',
      'sql_unittests',
      'sync_unit_tests',
      'telemetry_unittests',
      'ui_unittests',
      'unit_tests',
      'views_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 3,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Win7 Sync x64', 'rel_x64_sync', 'windows', 'win_x64_rel_trigger',
  notify_on_missing=True)
F('rel_x64_sync', win_tester().ChromiumFactory(
    slave_type='Tester',
    target='Release_x64',
    build_url=rel_x64_archive,
    tests=['sync_integration'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('NaCl Tests (x86-32)', 'rel_nacl', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)
F('rel_nacl', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['nacl_integration'],
    factory_properties={
      'process_dumps': True,
      'sharded_tests': sharded_tests,
      'start_crash_handler': True,
    }))

B('NaCl Tests (x86-64)', 'rel_nacl', 'testers|windows', 'win_rel_trigger',
  notify_on_missing=True)

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWin', 'Win Builder (dbg)',
                                          'cr-win-dbg', 'win32')

#
# Main debug scheduler for src/
#
S('win_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('win_dbg_trigger')

#
# Win x64 Dbg Builder
#
B('Win x64 Builder (dbg)', 'dbg_x64', 'compile|windows', 'win_dbg',
  builddir='cr-win-dbg-x64', auto_reboot=False, notify_on_missing=True)
F('dbg_x64', win_out().ChromiumFactory(
    slave_type='Builder',
    target='Debug_x64',
    options=['--compiler=goma',
             '--', 'all'],
    factory_properties={
      'gclient_env': {
        'GYP_DEFINES': 'component=shared_library fastbuild=1 target_arch=x64',
      }}))


#
# Win Dbg Builder
#
B('Win Builder (dbg)', 'dbg', 'compile|windows', 'win_dbg',
  builddir='cr-win-dbg', auto_reboot=False, notify_on_missing=True)
F('dbg', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['--compiler=goma'],
    project='all.sln;chromium_builder_tests',
    factory_properties={'gclient_env': {'GYP_DEFINES': 'fastbuild=1'},
                        'trigger': 'win_dbg_trigger'}))

#
# Win Dbg Unit testers
#
F('dbg_unit_1', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'ash_unittests',
      'aura',
      'base_unittests',
      'cacheinvalidation_unittests',
      'cast',
      'cc_unittests',
      'chrome_elf_unittests',
      'chromedriver_unittests',
      'check_deps',
      'components_unittests',
      'compositor',
      'courgette_unittests',
      'crypto_unittests',
      'events',
      'gcm_unit_tests',
      'gpu',
      'installer',
      'jingle',
      'media',
      'ppapi_unittests',
      'printing',
      'remoting',
      'unit',
      'url_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

F('dbg_unit_2', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'browser_tests',
      'content_browsertests',
      'net',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 1,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

F('dbg_unit_3', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'browser_tests',
      'sandbox',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 2,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

F('dbg_unit_4', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['browser_tests'],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 3,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

F('dbg_unit_5', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['browser_tests'],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 4,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

F('dbg_unit_6', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['browser_tests'],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 5,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Win7 Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)
B('Win7 Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)
B('Win7 Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)
B('Win7 Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)
B('Win7 Tests (dbg)(5)', 'dbg_unit_5', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)
B('Win7 Tests (dbg)(6)', 'dbg_unit_6', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)

#
# Win Dbg Interactive Tests
#
B('Interactive Tests (dbg)', 'dbg_int', 'testers|windows', 'win_dbg_trigger',
  notify_on_missing=True)
F('dbg_int', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['interactive_ui_tests'],
    factory_properties={
      'generate_gtest_json': True,
      'process_dumps': True,
      'sharded_tests': sharded_tests,
      'start_crash_handler': True,
    }))

#
# Dbg Aura Testers
#

B('Win8 Aura', 'dbg_aura_win8', 'windows',
  'win_dbg_trigger', notify_on_missing=True)
F('dbg_aura_win8', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['ash_unittests',
           'aura',
           'compositor',
           'events',
           'views_unittests',
          ],
    factory_properties={
      'generate_gtest_json': True,
      'process_dumps': True,
      'sharded_tests': sharded_tests,
      'start_crash_handler': True,
    }))

def Update(config, active_master, c):
  return helper.Update(c)
