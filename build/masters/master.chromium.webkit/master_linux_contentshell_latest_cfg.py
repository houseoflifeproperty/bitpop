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

defaults['category'] = '9content shell'

#
# Main release scheduler for WebKit
#
S('s1_contentshell_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Content Shell Layouttests
#

B('WebKit (Content Shell) Linux', 'f_contentshell_linux_rel',
  scheduler='s1_contentshell_webkit_rel')

F('f_contentshell_linux_rel', linux().ChromiumWebkitLatestFactory(
    target='Release',
    tests=[
        'webkit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'content_shell_builder',
    ],
    factory_properties={
        'additional_expectations_files': [
            ['content', 'shell', 'layout_tests', 'TestExpectations' ],
        ],
        'additional_drt_flag': '--dump-render-tree',
        'archive_webkit_results': True,
        'test_results_server': 'test-results.appspot.com',
        'driver_name': 'content_shell',
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
    }))


def Update(config, active_master, c):
  return helper.Update(c)
