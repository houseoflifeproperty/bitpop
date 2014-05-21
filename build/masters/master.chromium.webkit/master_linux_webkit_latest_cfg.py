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

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '6webkit linux latest'

#
# Main release scheduler for webkit
#
S('s6_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel Builder/Tester
#
B('WebKit Linux', 'f_webkit_linux_rel', scheduler='s6_webkit_rel')
F('f_webkit_linux_rel', linux().ChromiumWebkitLatestFactory(
    tests=[
        'test_shell',
        'webkit',
        'webkit_lint',
        'webkit_unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'DumpRenderTree',
        'test_shell',
        'test_shell_tests',
        'webkit_unit_tests',
    ],
    factory_properties={
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
    }))

B('WebKit Linux 32', 'f_webkit_linux_rel', scheduler='s6_webkit_rel')

asan_gyp = ('asan=1 linux_use_tcmalloc=0 '
            'release_extra_cflags="-g -O1 -fno-inline-functions -fno-inline"')

B('WebKit Linux ASAN', 'f_webkit_linux_rel_asan', scheduler='s6_webkit_rel',
  auto_reboot=False)
F('f_webkit_linux_rel_asan', linux().ChromiumWebkitLatestFactory(
    tests=['webkit'],
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
        '--',
        'DumpRenderTree'
    ],
    factory_properties={
        'additional_expectations_files': [
            ['webkit', 'tools', 'layout_tests', 'test_expectations_asan.txt' ],
        ],
        'gs_bucket': 'gs://webkit-asan',
        'gclient_env': {'GYP_DEFINES': asan_gyp, 'GYP_GENERATORS': 'ninja'},
        'time_out_ms': '18000'
    }))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s6_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Linux Dbg Webkit builders/testers
#

B('WebKit Linux (dbg)', 'f_webkit_dbg_tests', scheduler='s6_webkit_dbg',
  auto_reboot=False)
F('f_webkit_dbg_tests', linux().ChromiumWebkitLatestFactory(
    target='Debug',
    tests=[
        'test_shell',
        'webkit',
        'webkit_lint',
        'webkit_unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'test_shell',
        'test_shell_tests',
        'webkit_unit_tests',
        'DumpRenderTree',
    ],
    factory_properties={
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
    }))

def Update(config, active_master, c):
  return helper.Update(c)
