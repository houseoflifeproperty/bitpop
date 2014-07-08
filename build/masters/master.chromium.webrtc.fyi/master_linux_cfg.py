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


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')

S('linux_webrtc_scheduler', branch='trunk', treeStableTimer=0)
P('linux_periodic_scheduler', periodicBuildTimer=60*60)

tests = [
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'sizes',
]

defaults['category'] = 'linux'

B('Linux', 'linux_webrtc_factory',
  scheduler='linux_webrtc_scheduler|linux_periodic_scheduler',
  notify_on_missing=True)
F('linux_webrtc_factory', linux().ChromiumWebRTCLatestFactory(
    slave_type='BuilderTester',
    target='Release',
    options=['--compiler=goma', '--', 'chromium_builder_webrtc'],
    tests=tests,
    factory_properties={
        'use_xvfb_on_linux': True,
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-linux',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
    }))


def Update(config, active_master, c):
  helper.Update(c)
