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


def mac():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

S('mac_rel_scheduler', branch='src', treeStableTimer=60)
T('mac_rel_trigger')

chromium_rel_mac_archive = master_config.GetArchiveUrl('ChromiumWebRTC',
    'Mac Builder',
    'chromium-webrtc-rel-mac-builder',
    'mac')

tests = [
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
]

defaults['category'] = 'mac'

B('Mac Builder', 'mac_rel_factory', scheduler='mac_rel_scheduler',
  builddir='chromium-webrtc-rel-mac-builder', notify_on_missing=True)
F('mac_rel_factory', mac().ChromiumWebRTCFactory(
    slave_type='Builder',
    target='Release',
    options=['--compiler=goma-clang', '--', '-target',
             'chromium_builder_webrtc'],
    factory_properties={'trigger': 'mac_rel_trigger',}))

B('Mac Tester', 'mac_tester_factory', scheduler='mac_rel_trigger')
F('mac_tester_factory', mac().ChromiumWebRTCFactory(
    slave_type='Tester',
    build_url=chromium_rel_mac_archive,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'halt_on_missing_build': True,
        'perf_id': 'chromium-webrtc-rel-mac',
    }))


def Update(config, active_master, c):
  helper.Update(c)
