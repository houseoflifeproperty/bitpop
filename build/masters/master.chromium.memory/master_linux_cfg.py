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

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

defaults['category'] = '1linux asan'

#
# Main asan release scheduler for src/
#
S('linux_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('linux_asan_rel_trigger')

linux_asan_archive = master_config.GetArchiveUrl('ChromiumMemory',
                                                 'Linux ASAN Builder',
                                                 'Linux_ASAN_Builder',
                                                 'linux')
#
# Linux ASAN Rel Builder
#
B('Linux ASAN Builder', 'linux_asan_rel', 'compile', 'linux_asan_rel',
  auto_reboot=False, notify_on_missing=True)
# Please do not add release_extra_cflags=-g here until the debug info section
# produced by Clang on Linux is small enough.
F('linux_asan_rel', linux().ChromiumASANFactory(
    slave_type='Builder',
    options=[
      '--compiler=goma-clang',
      '--build-tool=ninja',
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'device_unittests',
      'googleurl_unittests',
      'gpu_unittests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'net_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sandbox_linux_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
    ],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES': ('asan=1 '
                            'linux_use_tcmalloc=0 '),
            'GYP_GENERATORS': 'ninja', },
        'trigger': 'linux_asan_rel_trigger' }))

#
# Linux ASAN Rel testers
#
B('Linux ASAN Tests (1)', 'linux_asan_rel_tests_1', 'testers',
  'linux_asan_rel_trigger', notify_on_missing=True)
F('linux_asan_rel_tests_1', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=linux_asan_archive,
    tests=[
      'base',
      'browser_tests',
      'cacheinvalidation',
      'crypto',
      'device_unittests',
      'gpu',
      'jingle',
      'net',
      'sandbox_linux_unittests',
    ],
    factory_properties={'asan': True,
                        'browser_total_shards': 3,
                        'browser_shard_index': 1 }))

B('Linux ASAN Tests (2)', 'linux_asan_rel_tests_2', 'testers',
  'linux_asan_rel_trigger', notify_on_missing=True)
F('linux_asan_rel_tests_2', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=linux_asan_archive,
    tests=[
      'browser_tests',
      'googleurl',
      'media',
      'ppapi_unittests',
      'printing',
      'remoting',
      'unit',
    ],
    factory_properties={'asan': True,
                        'browser_total_shards': 3,
                        'browser_shard_index': 2 }))

B('Linux ASAN Tests (3)', 'linux_asan_rel_tests_3', 'testers',
  'linux_asan_rel_trigger', notify_on_missing=True)
F('linux_asan_rel_tests_3', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=linux_asan_archive,
    tests=[
      'browser_tests',
      'content_browsertests',
    ],
    factory_properties={'asan': True,
                        'browser_total_shards': 3,
                        'browser_shard_index': 3 }))

def Update(config, active_master, c):
  return helper.Update(c)
