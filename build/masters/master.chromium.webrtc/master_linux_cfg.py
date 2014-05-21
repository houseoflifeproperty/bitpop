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


def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

# Scheduler for the WebRTC trunk branch.
S('linux_rel_scheduler', branch='trunk', treeStableTimer=0)
T('linux_rel_trigger')

chromium_rel_linux_archive = master_config.GetArchiveUrl('ChromiumWebRTC',
    'Linux Builder',
    'chromium-webrtc-rel-linux-builder',
    'linux')

tests = ['pyauto_webrtc_tests']

defaults['category'] = 'linux'

B('Linux Builder', 'linux_rel_factory', scheduler='linux_rel_scheduler',
  builddir='chromium-webrtc-rel-linux-builder', notify_on_missing=True)
F('linux_rel_factory', linux().ChromiumWebRTCLatestFactory(
    slave_type='Builder',
    target='Release',
    options=['--compiler=goma', 'chromium_builder_webrtc'],
    factory_properties={'lkgr': True,
                        'trigger': 'linux_rel_trigger',}))

B('Linux Tester', 'linux_tester_factory', scheduler='linux_rel_trigger')
F('linux_tester_factory', linux().ChromiumWebRTCLatestFactory(
    slave_type='Tester',
    build_url=chromium_rel_linux_archive,
    tests=tests,
    factory_properties={'use_xvfb_on_linux': True,
                        'show_perf_results': True,
                        'halt_on_missing_build': True,
                        'perf_id': 'chromium-webrtc-rel-linux',}))


def Update(config, active_master, c):
  return helper.Update(c)
