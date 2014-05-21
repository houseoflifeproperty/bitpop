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

def chromiumos(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

defaults['category'] = '1linux'

rel_archive = master_config.GetArchiveUrl('ChromiumChromiumOS',
                                          'Linux ChromiumOS Builder',
                                          'chromium-rel-linux-chromeos',
                                          'linux')

S(name='chromium_local', branch='src', treeStableTimer=60)

T('chromiumos_rel_trigger')

# Tests that are single-machine shard-safe. For now we only use the sharding
# supervisor for long tests (more than 30 seconds) that are known to be stable.
sharded_tests = [
  'base_unittests',
  'browser_tests',
  'content_browsertests',
  'content_unittests',
  'media_unittests',
]

linux_chromeos_tests = [
  ('ash_unittests', 'aura_builder', 1),
  ('aura', 'aura_builder', 1),
  ('base', 'base_unittests', 1),
  ('browser_tests', 'browser_tests', 2),
  ('cacheinvalidation', 'cacheinvalidation_unittests', 1),
  ('chromeos_unittests', 'chromeos_unittests', 1),
  ('compositor', 'compositor_unittests', 1),
  ('content_browsertests', 'content_browsertests', 2),
  ('content_unittests', 'content_unittests', 1),
  ('crypto', 'crypto_unittests', 1),
  ('dbus', 'dbus_unittests', 1),
  ('device_unittests', 'device_unittests', 1),
  ('googleurl', 'googleurl_unittests', 1),
  (None, 'googleurl_unittests', 1),
  ('gpu', 'gpu_unittests', 1),
  ('interactive_ui', 'interactive_ui_tests', 3),
  ('jingle', 'jingle_unittests', 1),
  ('media', 'media_unittests', 1),
  ('net', 'net_unittests', 1),
  ('ppapi_unittests', 'ppapi_unittests', 1),
  ('printing', 'printing_unittests', 1),
  ('remoting', 'remoting_unittests', 1),
  #('safe_browsing', 'safe_browsing_tests', 0),
  ('sandbox_linux_unittests', 'sandbox_linux_unittests', 1),
  ('ui_unittests', 'ui_unittests', 1),
  ('unit_ipc', 'ipc_tests', 1),
  ('unit_sql', 'sql_unittests', 1),
  ('unit_sync', 'sync_unit_tests', 1),
  ('unit_unit', 'unit_tests', 1),
  ('views', 'views_unittests', 1),
]

def without_tests(pairs, without):
  return [(a, b, c) for (a, b, c) in pairs if not a in without]

def extract_tests(pairs, shard):
  return list(set(a for (a, _, c) in pairs if a and c == shard))

def extract_options(pairs):
  return list(set(b for (_, b, c) in pairs if b and c))

def prepend_type(prefix, tests):
  return ['%s_%s' % (prefix, value) for value in tests]


B('Linux ChromiumOS Full',
  factory='fullbuilder',
  gatekeeper='compile',
  # This shows up in the archived artifacts.
  builddir='Linux_ChromiumOS',
  scheduler='chromium_local',
  auto_reboot=False,
  notify_on_missing=True)
F('fullbuilder', chromiumos().ChromiumOSFactory(
    slave_type='BuilderTester',
    clobber=True,
    options=['--compiler=goma'] + extract_options(linux_chromeos_tests),
    tests=['check_deps2git',
           'check_licenses',
           'check_perms',],
    factory_properties={
        'archive_build': True,
        'gs_bucket': 'gs://chromium-browser-snapshots',
        'gs_acl': 'public-read',
        'show_perf_results': False,
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1'
                            ' component=static_library')},
        'window_manager': False}))


B('Linux ChromiumOS Builder',
  factory='builder',
  gatekeeper='compile',
  builddir='chromium-rel-linux-chromeos',
  scheduler='chromium_local',
  auto_reboot=False,
  notify_on_missing=True)
F('builder', chromiumos().ChromiumOSFactory(
    slave_type='Builder',
    options=['--compiler=goma'] + extract_options(linux_chromeos_tests),
    factory_properties={
        'archive_build': False,
        'trigger': 'chromiumos_rel_trigger',
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1'
                            ' component=shared_library')},
        'window_manager': False}))

B('Linux ChromiumOS Tests (1)',
  factory='tester_1',
  scheduler='chromiumos_rel_trigger',
  gatekeeper='tester',
  notify_on_missing=True)
F('tester_1', chromiumos().ChromiumOSFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=extract_tests(linux_chromeos_tests, 1),
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,
                        'chromeos': 1}))


B('Linux ChromiumOS Tests (2)',
  factory='tester_2',
  scheduler='chromiumos_rel_trigger',
  gatekeeper='tester',
  notify_on_missing=True)
F('tester_2', chromiumos().ChromiumOSFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=extract_tests(linux_chromeos_tests, 2) +
          extract_tests(linux_chromeos_tests, 3),
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,
                        'chromeos': 1}))


B('Linux ChromiumOS (Clang dbg)',
  factory='clang',
  gatekeeper='compile|tester',
  builddir='chromium-dbg-linux-chromeos-clang',
  scheduler='chromium_local',
  auto_reboot=False,
  notify_on_missing=True)
F('clang', chromiumos().ChromiumOSFactory(
    target='Debug',
    tests=[],
    options=['--compiler=clang'] + extract_options(linux_chromeos_tests),
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1 target_arch=ia32'
                            ' clang=1 clang_use_chrome_plugins=1'
                            ' fastbuild=1'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1'
                            ' component=shared_library'
                           )}}))
#
# Triggerable scheduler for the dbg builders
#
T('chromiumos_dbg_trigger')

dbg_archive = master_config.GetArchiveUrl('ChromiumChromiumOS',
                                          'Linux ChromiumOS Builder (dbg)',
                                          'Linux_ChromiumOS_Builder__dbg_',
                                          'linux')

B('Linux ChromiumOS Builder (dbg)', 'dbg', 'compile',
  'chromium_local', auto_reboot=False, notify_on_missing=True)
F('dbg', chromiumos().ChromiumOSFactory(
    slave_type='Builder',
    target='Debug',
    options=['--compiler=goma'] + extract_options(linux_chromeos_tests),
    factory_properties={
      'gclient_env': { 'GYP_DEFINES' : 'chromeos=1 component=shared_library' },
      'trigger': 'chromiumos_dbg_trigger',
      'window_manager': False,
    }))

B('Linux ChromiumOS Tests (dbg)(1)', 'dbg_tests_1', 'tester',
  'chromiumos_dbg_trigger', notify_on_missing=True)
F('dbg_tests_1', chromiumos().ChromiumOSFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=extract_tests(linux_chromeos_tests, 1),
    factory_properties={'chromeos': 1,
                        'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,}))


B('Linux ChromiumOS Tests (dbg)(2)', 'dbg_tests_2', 'tester',
  'chromiumos_dbg_trigger', notify_on_missing=True)
F('dbg_tests_2', chromiumos().ChromiumOSFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=extract_tests(linux_chromeos_tests, 2),
    factory_properties={'chromeos': 1,
                        'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,}))


B('Linux ChromiumOS Tests (dbg)(3)', 'dbg_tests_3', 'tester',
  'chromiumos_dbg_trigger', notify_on_missing=True)
F('dbg_tests_3', chromiumos().ChromiumOSFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=extract_tests(linux_chromeos_tests, 3),
    factory_properties={'chromeos': 1,
                        'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,}))



def Update(config, active_master, c):
  return helper.Update(c)
