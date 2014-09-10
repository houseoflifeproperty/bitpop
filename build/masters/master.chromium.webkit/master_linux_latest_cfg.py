# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import annotator_factory
from master.factory import chromium_factory

m_annotator = annotator_factory.AnnotatorFactory()

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


B('Linux GN', 'f_linux_gn', scheduler='global_scheduler')
F('f_linux_gn', m_annotator.BaseFactory('chromium_gn'))

B('Android GN', 'f_android_gn', scheduler='global_scheduler')
F('f_android_gn', m_annotator.BaseFactory('chromium_gn'))


def Update(_config, _active_master, c):
  return helper.Update(c)
