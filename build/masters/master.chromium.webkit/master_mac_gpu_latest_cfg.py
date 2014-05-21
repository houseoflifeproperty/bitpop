# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '9gpu'

#
# Main release scheduler for webkit
#
S('s9_gpu_mac_webkit_rel', branch='trunk', treeStableTimer=60)

#
# GPU Mac Release
#
B('GPU Mac10.7', 'f_gpu_mac_rel', scheduler='s9_gpu_mac_webkit_rel')
F('f_gpu_mac_rel', mac().ChromiumWebkitLatestFactory(
    target='Release',
    options=['--build-tool=ninja', '--compiler=goma-clang',
             'chromium_gpu_builder'],
    tests=[
      'gl_tests',
      'gpu_frame_rate',
      'gpu_latency',
      'gpu_throughput',
      'gpu_tests',
      'gpu_content_tests',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'perf_id': 'gpu-webkit-mac',
        'show_perf_results': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
    }))

################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s9_gpu_mac_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# GPU Mac Debug
#
B('GPU Mac10.7 (dbg)', 'f_gpu_mac_dbg', scheduler='s9_gpu_mac_webkit_dbg')
F('f_gpu_mac_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--build-tool=ninja', '--compiler=goma-clang',
             'chromium_gpu_debug_builder'],
    tests=[
      'gl_tests',
      'gpu_tests',
      'gpu_content_tests',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
    }))

def Update(config, active_master, c):
  return helper.Update(c)
