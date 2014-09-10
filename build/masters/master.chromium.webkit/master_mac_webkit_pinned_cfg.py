# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# WebKit test builders using the Skia graphics library.

from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
T = helper.Triggerable
F = helper.Factory

def mac():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

def mac_out():
  return chromium_factory.ChromiumFactory('src/out', 'darwin')

defaults['category'] = 'deps'

################################################################################
## Release
################################################################################

# Archive location
rel_builddir = 'webkit-mac-pinned-rel'
rel_archive = master_config.GetGSUtilUrl(
    'chromium-build-transfer', 'WebKit Mac Builder (deps)')

#
# Triggerable scheduler for the dbg builder
#
T('s2_chromium_rel_trigger')

#
# Mac Rel Builder
#
B('WebKit Mac Builder (deps)', 'f_webkit_mac_rel', auto_reboot=False,
  scheduler='global_deps_scheduler', builddir=rel_builddir)
F('f_webkit_mac_rel', mac_out().ChromiumFactory(
    slave_type='Builder',
    build_url=rel_archive,
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
        'blink_tests'],
    factory_properties={
        'trigger': 's2_chromium_rel_trigger',
        'gclient_env': {
            'GYP_DEFINES': 'fastbuild=1',
            'GYP_GENERATORS':'ninja',
        },
    }))

#
# Mac Rel WebKit testers
#
B('WebKit Mac10.6 (deps)', 'f_webkit_rel_tests',
  scheduler='s2_chromium_rel_trigger')
F('f_webkit_rel_tests', mac().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=chromium_factory.blink_tests,
    factory_properties={
      'additional_expectations': [
        ['webkit', 'tools', 'layout_tests', 'test_expectations.txt' ],
      ],
      'archive_webkit_results': ActiveMaster.is_production_host,
      'generate_gtest_json': True,
      'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
##
################################################################################

def Update(_config, _active_master, c):
  return helper.Update(c)
