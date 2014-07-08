# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = 'nonlayout'

#
# Linux Rel tests
#
B('Linux Tests', 'f_linux_tests_rel', scheduler='global_scheduler')
F('f_linux_tests_rel', linux().ChromiumFactory(
    tests=[
        'browser_tests',
        'cc_unittests',
        'content_browsertests',
        'interactive_ui_tests',
        'unit',
        'webkit_compositor_bindings_unittests',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma'
    ],
    factory_properties={
        'archive_build': True,
        'blink_config': 'blink',
        'build_name': 'Linux_x64',
        'generate_gtest_json': True,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'gs_bucket': 'gs://chromium-webkit-snapshots',
    }))

B('Linux Tests (dbg)', 'f_linux_tests_dbg', scheduler='global_scheduler')
F('f_linux_tests_dbg', linux().ChromiumFactory(
    target='Debug',
    tests=[
        'browser_tests',
        'cc_unittests',
        'content_browsertests',
        'interactive_ui_tests',
        'unit',
        'webkit_compositor_bindings_unittests',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma'
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'blink_config': 'blink',
    }))

linux_aura_build_targets = [
    'aura_builder',
    'base_unittests',
    'browser_tests',
    'cacheinvalidation_unittests',
    'compositor_unittests',
    'content_browsertests',
    'content_unittests',
    'crypto_unittests',
    'device_unittests',
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
    'ui_unittests',
    'url_unittests',
]

B('Linux Aura', 'f_linux_aura_rel', scheduler='global_scheduler')
F('f_linux_aura_rel', linux().ChromiumFactory(
    tests=[
        'aura',
        # This seems to have many failures
        #'content_browsertests',
        'unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
    ] + linux_aura_build_targets,
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {'GYP_DEFINES': 'use_aura=1', 'GYP_GENERATORS': 'ninja'},
        'window_manager': 'False',
        'blink_config': 'blink',
    }))


def Update(_config, _active_master, c):
  return helper.Update(c)
