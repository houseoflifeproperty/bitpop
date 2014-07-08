# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def win():
  return chromium_factory.ChromiumFactory('src/out', 'win32')

defaults['category'] = 'layout'

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Win Builder',
                                          'webkit-win-latest-rel', 'win32')

#
# Triggerable scheduler for testers
#
T('s4_webkit_rel_trigger')

#
# Win Rel Builder
#
B('WebKit Win Builder', 'f_webkit_win_rel',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel',
  auto_reboot=False)
F('f_webkit_win_rel', win().ChromiumFactory(
    slave_type='Builder',
    options=['--build-tool=ninja', '--', 'blink_tests'],
    factory_properties={
        'trigger': 's4_webkit_rel_trigger',
        'blink_config': 'blink',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
    }))

#
# Win Rel WebKit testers
#
B('WebKit XP', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger')
F('f_webkit_rel_tests', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=chromium_factory.blink_tests,
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('WebKit Win7', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger')

#
# Win x64 Rel Builder (note: currently no x64 testers)
#
B('WebKit Win x64 Builder', 'f_webkit_win_rel_x64',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel-x64',
  auto_reboot=False)
F('f_webkit_win_rel_x64', win().ChromiumFactory(
    slave_type='Builder',
    target='Release_x64',
    options=['--build-tool=ninja', '--', 'blink_tests'],
    factory_properties={
        'blink_config': 'blink',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES': 'component=shared_library target_arch=x64',
        },
    }))

B('WebKit Win Oilpan', 'f_webkit_win_oilpan_rel', scheduler='global_scheduler')
F('f_webkit_win_oilpan_rel', win().ChromiumFactory(
    tests=chromium_factory.blink_tests,
    options=['--build-tool=ninja', '--', 'blink_tests'],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'OilpanExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'blink_config': 'blink',
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_DEFINES':'enable_oilpan=1',
            'GYP_GENERATORS':'ninja',
        },
        'test_results_server': 'test-results.appspot.com',
    }))


################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Win Builder (dbg)',
                                          'webkit-win-latest-dbg', 'win32')
#
# Triggerable scheduler for testers
#
T('s4_webkit_dbg_trigger')

#
# Win Dbg Builder
#
B('WebKit Win Builder (dbg)', 'f_webkit_win_dbg', scheduler='global_scheduler',
  builddir='webkit-win-latest-dbg', auto_reboot=False)
F('f_webkit_win_dbg', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['--build-tool=ninja', '--', 'blink_tests'],
    factory_properties={
        'trigger': 's4_webkit_dbg_trigger',
        'blink_config': 'blink',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
    }))

#
# Win Dbg WebKit testers
#

B('WebKit Win7 (dbg)', 'f_webkit_dbg_tests',
    scheduler='s4_webkit_dbg_trigger')
F('f_webkit_dbg_tests', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=chromium_factory.blink_tests,
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('WebKit Win Oilpan (dbg)', 'f_webkit_win_oilpan_dbg',
  scheduler='global_scheduler')
F('f_webkit_win_oilpan_dbg', win().ChromiumFactory(
    target='Debug',
    tests=chromium_factory.blink_tests,
    options=['--build-tool=ninja', '--', 'blink_tests'],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'OilpanExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'blink_config': 'blink',
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_DEFINES':'enable_oilpan=1',
            'GYP_GENERATORS':'ninja',
        },
        'test_results_server': 'test-results.appspot.com',
    }))


#
# Win x64 Dbg Builder (note: currently no x64 testers)
#
B('WebKit Win x64 Builder (dbg)', 'f_webkit_win_dbg_x64',
  scheduler='global_scheduler', builddir='webkit-win-latest-dbg-x64',
  auto_reboot=False)
F('f_webkit_win_dbg_x64', win().ChromiumFactory(
    slave_type='Builder',
    target='Debug_x64',
    options=['--build-tool=ninja', '--', 'blink_tests'],
    factory_properties={
        'blink_config': 'blink',
        'gclient_env': {
          'GYP_GENERATORS':'ninja',
          'GYP_DEFINES': 'component=shared_library fastbuild=1 target_arch=x64',
        },
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
