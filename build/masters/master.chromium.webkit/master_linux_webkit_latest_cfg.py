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

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')

defaults['category'] = 'layout'


################################################################################
## Release
################################################################################

#
# Linux Rel Builder/Tester
#
B('WebKit Linux', 'f_webkit_linux_rel', scheduler='global_scheduler')
F('f_webkit_linux_rel', linux().ChromiumFactory(
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': {
          'GYP_GENERATORS': 'ninja',
        },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('WebKit Linux 32', 'f_webkit_linux_rel', scheduler='global_scheduler')

B('WebKit Linux Oilpan', 'f_webkit_linux_oilpan_rel',
    scheduler='global_scheduler')
F('f_webkit_linux_oilpan_rel', linux().ChromiumFactory(
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'OilpanExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': {
          'GYP_DEFINES': 'enable_oilpan=1',
          'GYP_GENERATORS': 'ninja',
        },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

asan_gyp = ('asan=1 use_allocator=none '
            'release_extra_cflags="-g -O1 -fno-inline-functions -fno-inline"')

B('WebKit Linux ASAN', 'f_webkit_linux_rel_asan', scheduler='global_scheduler',
    auto_reboot=False)
F('f_webkit_linux_rel_asan', linux().ChromiumFactory(
    tests=['webkit'],
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
        '--',
        'blink_tests'
    ],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'ASANExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'asan': True,
        'blink_config': 'blink',
        'gclient_env': {
          'GYP_DEFINES': asan_gyp,
          'GYP_GENERATORS': 'ninja',
        },
        'generate_gtest_json': True,
        'gs_bucket': 'gs://webkit-asan',
        'test_results_server': 'test-results.appspot.com',
        'time_out_ms': '48000',  # ASAN is roughly 8x slower than Release.
    }))

B('WebKit Linux Leak', 'f_webkit_linux_leak_rel', scheduler='global_scheduler')
F('f_webkit_linux_leak_rel', linux().ChromiumFactory(
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'LeakExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': {
          'GYP_GENERATORS': 'ninja',
        },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
        'webkit_test_options': ['--enable-leak-detection'],
    }))

B('WebKit Linux Oilpan Leak', 'f_webkit_linux_oilpan_leak_rel',
    scheduler='global_scheduler')
F('f_webkit_linux_oilpan_leak_rel', linux().ChromiumFactory(
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'OilpanExpectations' ],
            ['third_party', 'WebKit', 'LayoutTests', 'LeakExpectations' ],
            ['third_party', 'WebKit', 'LayoutTests', 'OilpanLeakExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'gclient_env': {
            'GYP_DEFINES': 'enable_oilpan=1',
            'GYP_GENERATORS':'ninja',
        },
        'blink_config': 'blink',
        'webkit_test_options': ['--enable-leak-detection'],
    }))


################################################################################
## Debug
################################################################################

#
# Linux Dbg Webkit builders/testers
#

B('WebKit Linux (dbg)', 'f_webkit_dbg_tests', scheduler='global_scheduler',
    auto_reboot=False)
F('f_webkit_dbg_tests', linux().ChromiumFactory(
    target='Debug',
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
        'blink_config': 'blink',
    }))

B('WebKit Linux Oilpan (dbg)', 'f_webkit_linux_oilpan_dbg',
    scheduler='global_scheduler')
F('f_webkit_linux_oilpan_dbg', linux().ChromiumFactory(
    target='Debug',
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'additional_expectations': [
            ['third_party', 'WebKit', 'LayoutTests', 'OilpanExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': {
          'GYP_DEFINES': 'enable_oilpan=1',
          'GYP_GENERATORS': 'ninja',
        },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))


def Update(_config, _active_master, c):
  return helper.Update(c)
