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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '8mac latest'

#
# Main release scheduler for webkit
#
S('s8_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Mac Rel Builder
#
B('Mac10.6 Tests', 'f_mac_tests_rel', scheduler='s8_webkit_rel')
F('f_mac_tests_rel', mac().ChromiumWebkitLatestFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_tests'],
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui',
      'unit',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
    }))

B('Mac10.6 Perf', 'f_mac_perf6_rel', scheduler='s8_webkit_rel')
F('f_mac_perf6_rel', mac().ChromiumWebkitLatestFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_perf'],
    tests=[
      'dom_perf',
      'dromaeo',
      'memory',
      'page_cycler_bloat-http',
      'page_cycler_database',
      'page_cycler_dhtml',
      'page_cycler_indexeddb',
      'page_cycler_intl1',
      'page_cycler_intl2',
      'page_cycler_morejs',
      'page_cycler_moz',
      'page_cycler_moz-http',
      'startup',
      'sunspider',
      'tab_switching',
      'octane',
    ],
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-rel-mac6-webkit',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES': 'fastbuild=1',
        },
    }))

B('Mac10.8 Tests', 'f_mac_tests_rel_108', scheduler='s8_webkit_rel')
F('f_mac_tests_rel_108', mac().ChromiumWebkitLatestFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_tests'],
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui',
      'unit',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
    }))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s8_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'f_mac_dbg', scheduler='s8_webkit_dbg')
F('f_mac_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--', '-project', '../webkit/webkit.xcodeproj',]))

def Update(config, active_master, c):
  return helper.Update(c)
