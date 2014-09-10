# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def mac():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

def mac_out():
  return chromium_factory.ChromiumFactory('src/out', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = 'nonlayout'

#
# Mac Rel Builder
#
B('Mac10.6 Tests', 'f_mac_tests_rel', scheduler='global_scheduler')
F('f_mac_tests_rel', mac_out().ChromiumFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_tests'],
    tests=[
      'browser_tests',
      'cc_unittests',
      'content_browsertests',
      'interactive_ui_tests',
      'telemetry_unittests',
      'unit',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
        'blink_config': 'blink',
    }))


B('Mac10.8 Tests', 'f_mac_tests_rel_108', scheduler='global_scheduler')
F('f_mac_tests_rel_108', mac_out().ChromiumFactory(
    # Build 'all' instead of 'chromium_builder_tests' so that archiving works.
    # TODO: Define a new build target that is archive-friendly?
    options=['--build-tool=ninja', '--compiler=goma-clang', '--', 'all'],
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui_tests',
      'telemetry_unittests',
      'unit',
    ],
    factory_properties={
        'archive_build': True,
        'blink_config': 'blink',
        'build_name': 'Mac',
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
        'gs_bucket': 'gs://chromium-webkit-snapshots',
    }))


################################################################################
## Debug
################################################################################

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'f_mac_dbg', scheduler='global_scheduler')
F('f_mac_dbg', mac().ChromiumFactory(
    target='Debug',
    options=['--compiler=goma-clang', '--', '-target', 'blink_tests'],
    factory_properties={
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
