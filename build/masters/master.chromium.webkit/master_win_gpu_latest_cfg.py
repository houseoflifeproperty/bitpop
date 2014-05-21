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
T = helper.Triggerable

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

defaults['category'] = '9gpu'

################################################################################
## Release
################################################################################

# Main release scheduler for webkit
S('s9_gpu_win_webkit_rel', branch='trunk', treeStableTimer=60)

#
# GPU Win Release
#
B('GPU Win7 (NVIDIA)', 'f_gpu_win_rel',
  scheduler='s9_gpu_win_webkit_rel')
F('f_gpu_win_rel', win().ChromiumWebkitLatestFactory(
    target='Release',
    slave_type='BuilderTester',
    tests=[
      'gl_tests',
      'gpu_frame_rate',
      'gpu_latency',
      'gpu_throughput',
      'gpu_tests',
      'gpu_content_tests',
    ],
    project='all.sln;chromium_gpu_builder',
    factory_properties={'generate_gtest_json': True,
                        'start_crash_handler': True,
                        'perf_id': 'gpu-webkit-win7-nvidia',
                        'show_perf_results': True,
                        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'}}))

################################################################################
## Debug
################################################################################


#
# Main debug scheduler for webkit
#
S('s9_gpu_win_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# GPU Win Debug
#
B('GPU Win7 (dbg) (NVIDIA)', 'f_gpu_win_dbg',
  scheduler='s9_gpu_win_webkit_dbg')
F('f_gpu_win_dbg', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='BuilderTester',
    tests=[
      'gl_tests',
      'gpu_tests',
      'gpu_content_tests',
    ],
    project='all.sln;chromium_gpu_debug_builder',
    factory_properties={'generate_gtest_json': True,
                        'start_crash_handler': True,
                        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'}}))


def Update(config, active_master, c):
  return helper.Update(c)
