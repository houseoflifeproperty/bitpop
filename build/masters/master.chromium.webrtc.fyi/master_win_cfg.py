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
P = helper.Periodic


def Win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')
def WinXpTester():
  return chromium_factory.ChromiumFactory('src/build', 'win32',
                                          nohooks_on_update=True)


S('win_rel_scheduler', branch='trunk', treeStableTimer=0)
P('win_periodic_scheduler', periodicBuildTimer=4*60*60)
T('win_rel_trigger')


chromium_rel_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                  'win_rel-fyi')


tests = [
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'sizes',
]


defaults['category'] = 'win'


B('Win Builder', 'win_webrtc_factory',
  scheduler='win_rel_scheduler|win_periodic_scheduler', notify_on_missing=True)
F('win_webrtc_factory', Win().ChromiumWebRTCLatestFactory(
    slave_type='Builder',
    target='Release',
    options=['--compiler=goma', '--', 'chromium_builder_webrtc'],
    compile_timeout=2400,
    factory_properties={
        'trigger': 'win_rel_trigger',
        'build_url': chromium_rel_archive,
    }))


B('WinXP Tester', 'win_xp_tester_factory',
  scheduler='win_rel_trigger')
F('win_xp_tester_factory', WinXpTester().ChromiumWebRTCLatestFactory(
    slave_type='Tester',
    build_url=chromium_rel_archive,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'halt_on_missing_build': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-winxp',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'process_dumps': True,
        'start_crash_handler': True,
    }))


B('Win7 Tester', 'win_7_tester_factory',
  scheduler='win_rel_trigger')
F('win_7_tester_factory', Win().ChromiumWebRTCLatestFactory(
    slave_type='Tester',
    build_url=chromium_rel_archive,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'halt_on_missing_build': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-win7',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'process_dumps': True,
        'start_crash_handler': True,
    }))


def Update(config, active_master, c):
  return helper.Update(c)
