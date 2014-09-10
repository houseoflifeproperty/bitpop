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

defaults['category'] = 'deps'

################################################################################
## Release
################################################################################

#
# Linux Rel Builder
#
B('WebKit Linux (deps)', 'f_webkit_linux_rel',
  scheduler='global_deps_scheduler')
F('f_webkit_linux_rel', linux().ChromiumFactory(
    tests=chromium_factory.blink_tests,
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'blink_tests',
    ],
    factory_properties={
        'additional_expectations': [
            ['webkit', 'tools', 'layout_tests', 'test_expectations.txt' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
