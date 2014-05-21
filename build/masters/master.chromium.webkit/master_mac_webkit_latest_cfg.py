# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# WebKit test builders using the Skia graphics library.
#
# Note that we use the builder vs tester role separation differently
# here than in our other buildbot configurations.
#
# In this configuration, the testers build the tests themselves rather than
# extracting them from the builder.  That's because these testers always
# fetch from webkit HEAD, and by the time the tester runs, webkit HEAD may
# point at a different revision than it did when the builder fetched webkit.
#
# Even though the testers don't extract the build package from the builder,
# the builder is still useful because it can cycle more quickly than the
# builder+tester can, and can alert us more quickly to build breakages.
#
# If you have questions about this, you can ask nsylvain.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '5webkit mac latest'

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Mac Builder',
                                          'webkit-mac-latest-rel', 'mac')

#
# Main release scheduler for webkit
#
S('s5_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for testers
#
T('s5_webkit_rel_trigger')

#
# Mac Rel Builder
#
B('WebKit Mac Builder', 'f_webkit_mac_rel', auto_reboot=False,
  scheduler='s5_webkit_rel', builddir='webkit-mac-latest-rel')
F('f_webkit_mac_rel', mac().ChromiumWebkitLatestFactory(
    slave_type='Builder',
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
        'test_shell', 'test_shell_tests', 'webkit_unit_tests',
        'DumpRenderTree'],
    factory_properties={
        'trigger': 's5_webkit_rel_trigger',
        'gclient_env': {
            'GYP_DEFINES':'use_skia=1 fastbuild=1',
            'GYP_GENERATORS':'ninja',
        },
        'layout_test_platform': 'chromium-mac',
    }))

#
# Mac Rel WebKit testers
#

B('WebKit Mac10.6', 'f_webkit_rel_tests_106', scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_106', mac().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'test_shell',
      'webkit',
      'webkit_lint',
      'webkit_unit',
    ],
    factory_properties={
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

B('WebKit Mac10.7', 'f_webkit_rel_tests_107', scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_107', mac().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'test_shell',
      'webkit',
      'webkit_lint',
      'webkit_unit',
    ],
    factory_properties={
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

B('WebKit Mac10.8', 'f_webkit_rel_tests_108', auto_reboot=False,
  scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_108', mac().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'test_shell',
      'webkit',
      'webkit_lint',
      'webkit_unit',
    ],
    factory_properties={
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Mac Builder (dbg)',
                                          'webkit-mac-latest-dbg', 'mac')

#
# Main debug scheduler for the builder
#
S('s5_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for testers
#
T('s5_webkit_dbg_trigger')

#
# Mac Dbg Builder
#
B('WebKit Mac Builder (dbg)', 'f_webkit_mac_dbg', auto_reboot=False,
  scheduler='s5_webkit_dbg', builddir='webkit-mac-latest-dbg')
F('f_webkit_mac_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder',
    options=[
        '--compiler=clang','--', '-project', '../webkit/webkit.xcodeproj'],
    factory_properties={
        'trigger': 's5_webkit_dbg_trigger',
        'gclient_env': {
            'GYP_DEFINES':'use_skia=1'
        },
        'layout_test_platform': 'chromium-mac',
    }))

#
# Mac Dbg WebKit testers
#

B('WebKit Mac10.6 (dbg)', 'f_webkit_dbg_tests',
  scheduler='s5_webkit_dbg_trigger')
F('f_webkit_dbg_tests', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'test_shell',
      'webkit',
      'webkit_lint',
      'webkit_unit',
    ],
    factory_properties={
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

B('WebKit Mac10.7 (dbg)', 'f_webkit_dbg_tests',
  scheduler='s5_webkit_dbg_trigger')


################################################################################
##
################################################################################

def Update(config, active_master, c):
  return helper.Update(c)
