# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')

defaults['category'] = 'nonlayout'

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
  'events_unittests',
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

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Win Builder',
                                          'win-latest-rel', 'win32')

# Triggerable scheduler for testers
T('s7_webkit_builder_rel_trigger')


#
# Win Rel Builders
#
B('Win Builder', 'f_win_rel', scheduler='global_scheduler',
  builddir='win-latest-rel', auto_reboot=False)
F('f_win_rel', win().ChromiumFactory(
    slave_type='Builder',
    options=['--build-tool=ninja', '--compiler=goma', 'chromium_builder'],
    factory_properties={
        'trigger': 's7_webkit_builder_rel_trigger',
        'gclient_env': {
            'GYP_DEFINES': 'fastbuild=1',
            'GYP_GENERATORS': 'ninja',
        },
        'archive_build': True,
        'blink_config': 'blink',
        'build_name': 'Win',
        'gs_bucket': 'gs://chromium-webkit-snapshots',
        'gs_acl': 'public-read',
    }))

#
# Win Rel testers+builders
#
# TODO: Switch back to trigger, http://crbug.com/102331

B('Win7 Tests', 'f_win_rel_tests', scheduler='s7_webkit_builder_rel_trigger')
F('f_win_rel_tests', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'installer',
      'browser_tests',
      'content_browsertests',
      'telemetry_unittests',
      'unit',
    ],
    factory_properties={
        'perf_id': 'chromium-rel-win7-webkit',
        'show_perf_results': True,
        'start_crash_handler': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

################################################################################
## Debug
################################################################################


#
# Win Dbg Builder
#
B('Win7 (dbg)', 'f_win_dbg', scheduler='global_scheduler',
  builddir='win-latest-dbg')
F('f_win_dbg', win().ChromiumFactory(
    target='Debug',
    options=['--build-tool=ninja', '--compiler=goma', 'chromium_builder'],
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui_tests',
      'telemetry_unittests',
      'unit',
    ],
    factory_properties={
        'sharded_tests': sharded_tests,
        'start_crash_handler': True,
        'generate_gtest_json': True,
        'gclient_env': {
             'GYP_DEFINES': 'fastbuild=1',
             'GYP_GENERATORS': 'ninja',
        },
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
