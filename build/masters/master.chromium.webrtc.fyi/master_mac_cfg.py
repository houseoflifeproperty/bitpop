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
P = helper.Periodic


def mac():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

S('mac_webrtc_scheduler', branch='trunk', treeStableTimer=0)
P('mac_periodic_scheduler', periodicBuildTimer=60*60)

options = ['--compiler=goma-clang', '--', '-target', 'chromium_builder_webrtc']
tests = [
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'sizes',
]

defaults['category'] = 'mac'

B('Mac', 'mac_webrtc_factory',
  scheduler='mac_webrtc_scheduler|mac_periodic_scheduler',
  notify_on_missing=True)
F('mac_webrtc_factory', mac().ChromiumWebRTCLatestFactory(
    slave_type='BuilderTester',
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-mac',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
    }))


def Update(config, active_master, c):
  return helper.Update(c)
