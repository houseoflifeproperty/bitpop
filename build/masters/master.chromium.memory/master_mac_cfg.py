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

def mac(): return chromium_factory.ChromiumFactory('src/out', 'darwin')

defaults['category'] = '2mac asan'

#
# Main asan release scheduler for src/
#
S('mac_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('mac_asan_rel_trigger')
T('mac_asan_64_rel_trigger')

# Tests that are single-machine shard-safe.
sharded_tests = [
  'aura_unittests',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cc_unittests',
  'chromedriver_tests',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'device_unittests',
  'gcm_unit_tests',
  'gpu_unittests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sync_integration_tests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'views_unittests',
  'webkit_compositor_bindings_unittests',
]

mac_asan_options = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cc_unittests',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'device_unittests',
  'gcm_unit_tests',
  'gpu_unittests',
  'interactive_ui_tests',
  'ipc_tests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sql_unittests',
  'sync_unit_tests',
  'ui_unittests',
  # TODO(glider): unit_tests is too large on 32-bit OSX to run under ASan. See
  # http://crbug.com/238398
  # 'unit_tests',
  'url_unittests',
]

# See above. It's ok to run unit_tests under ASan on 64-bit OSX.
mac_asan_64_options = mac_asan_options + ['unit_tests']

mac_asan_tests_1 = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cc_unittests',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'gcm_unit_tests',
  'gpu_unittests',
  'ipc_tests',
  'jingle',
  'media',
  'ppapi_unittests',
  'printing',
  'remoting',
  'unit_sql',
  'url_unittests',
]

mac_asan_tests_2 = [
  'browser_tests',
  'net',
  'sync_unit_tests',
  'ui_unittests',
]

mac_asan_tests_3 = [
  'browser_tests',
  'interactive_ui_tests',
]

mac_asan_archive = master_config.GetArchiveUrl(
    'ChromiumMemory',
    'Mac ASan Builder',
    'Mac_ASan_Builder',
    'mac')

mac_asan_64_archive = master_config.GetArchiveUrl(
    'ChromiumMemory',
    'Mac ASan 64 Builder',
    'Mac_ASan_64_Builder',
    'mac')

gclient_env = {
  'GYP_DEFINES': 'asan=1 release_extra_cflags=-gline-tables-only',
  'GYP_GENERATORS': 'ninja',
}

gclient_64_env = {
  'GYP_DEFINES': (
    'asan=1 '
    'release_extra_cflags=-gline-tables-only '
    'target_arch=x64 '
    'host_arch=x64'),
  'GYP_GENERATORS': 'ninja',
}

#
# Mac ASan Rel Builder
#
B('Mac ASan Builder', 'mac_asan_rel', 'compile', 'mac_asan_rel',
  auto_reboot=False, notify_on_missing=True)
F('mac_asan_rel', mac().ChromiumASANFactory(
    target='Release',
    slave_type='Builder',
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
    ] + mac_asan_options,
    factory_properties={
      'asan': True,
      'gclient_env': gclient_env,
      'package_dsym_files': True,
      'trigger': 'mac_asan_rel_trigger',
    },
))

#
# Mac ASan Rel testers
#
B('Mac ASan Tests (1)', 'mac_asan_rel_tests_1', 'testers',
  'mac_asan_rel_trigger', notify_on_missing=True)
F('mac_asan_rel_tests_1', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_1,
    factory_properties={
      'asan': True,
      'browser_shard_index': '1',
      'browser_total_shards': '3',
      'gclient_env': gclient_env,
      'sharded_tests': sharded_tests,
    }))


B('Mac ASan Tests (2)', 'mac_asan_rel_tests_2', 'testers',
  'mac_asan_rel_trigger', notify_on_missing=True)
F('mac_asan_rel_tests_2', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_2,
    factory_properties={
      'asan': True,
      'browser_shard_index': '2',
      'browser_total_shards': '3',
      'gclient_env': gclient_env,
      'sharded_tests': sharded_tests,
    }))

B('Mac ASan Tests (3)', 'mac_asan_rel_tests_3', 'testers',
  'mac_asan_rel_trigger', notify_on_missing=True)
F('mac_asan_rel_tests_3', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_3,
    factory_properties={
      'asan': True,
      'browser_shard_index': '3',
      'browser_total_shards': '3',
      'gclient_env': gclient_env,
      'sharded_tests': sharded_tests,
    }))

#
# Mac ASan 64-bit Rel Builder
#
B('Mac ASan 64 Builder', 'mac_asan_64_rel_f', 'compile', 'mac_asan_rel',
  auto_reboot=False, notify_on_missing=True)
F('mac_asan_64_rel_f', mac().ChromiumASANFactory(
    target='Release',
    slave_type='Builder',
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
    ] + mac_asan_64_options,
    factory_properties={
      'asan': True,
      'gclient_env': gclient_64_env,
      'package_dsym_files': True,
      'trigger': 'mac_asan_64_rel_trigger',
    },
))

#
# Mac ASan 64-bit Rel testers
#
B('Mac ASan 64 Tests (1)', 'mac_asan_64_rel_tests_1', 'testers',
  'mac_asan_64_rel_trigger', notify_on_missing=True)
F('mac_asan_64_rel_tests_1', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_64_archive,
    tests=mac_asan_tests_1 + ['unit_tests'],
    factory_properties={
      'asan': True,
      'browser_shard_index': '1',
      'browser_total_shards': '3',
      'gclient_env': gclient_64_env,
      'sharded_tests': sharded_tests,
    }))


B('Mac ASan 64 Tests (2)', 'mac_asan_64_rel_tests_2', 'testers',
  'mac_asan_64_rel_trigger', notify_on_missing=True)
F('mac_asan_64_rel_tests_2', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_64_archive,
    tests=mac_asan_tests_2,
    factory_properties={
      'asan': True,
      'browser_shard_index': '2',
      'browser_total_shards': '3',
      'gclient_env': gclient_64_env,
      'sharded_tests': sharded_tests,
    }))

B('Mac ASan 64 Tests (3)', 'mac_asan_64_rel_tests_3', 'testers',
  'mac_asan_64_rel_trigger', notify_on_missing=True)
F('mac_asan_64_rel_tests_3', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_64_archive,
    tests=mac_asan_tests_3,
    factory_properties={
      'asan': True,
      'browser_shard_index': '3',
      'browser_total_shards': '3',
      'gclient_env': gclient_64_env,
      'sharded_tests': sharded_tests,
    }))

def Update(config, active_master, c):
  return helper.Update(c)
