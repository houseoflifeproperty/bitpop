# Copyright 2014 The Chromium Authors. All rights reserved.
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


def android():
  return chromium_factory.ChromiumFactory('', 'linux2', nohooks_on_update=True,
                                          target_os='android')

S('android_webrtc_scheduler', branch='trunk', treeStableTimer=0)
P('android_periodic_scheduler', periodicBuildTimer=30*60)
T('android_trigger_dbg')

defaults['category'] = 'android'

android_dbg_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                 'android_chromium_dbg')

# Builders.
B('Android Builder (dbg)', 'android_builder_dbg_factory',
  scheduler='android_webrtc_scheduler|android_periodic_scheduler',
  notify_on_missing=True)
F('android_builder_dbg_factory', android().ChromiumWebRTCAndroidFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webrtc-chromium-builder-dbg',
        'build_url': android_dbg_archive,
        'trigger': 'android_trigger_dbg',
    }))

# Testers.
B('Android Tests (dbg) (KK Nexus5)', 'android_tests_n5_dbg_factory',
  scheduler='android_trigger_dbg', notify_on_missing=True)
F('android_tests_n5_dbg_factory', android().ChromiumWebRTCAndroidFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-chromium-tests-dbg',
      'build_url': android_dbg_archive,
      'perf_id': 'chromium-webrtc-dbg-android-nexus5',
      'show_perf_results': True,
      'test_platform': 'android',
    }))

B('Android Tests (dbg) (JB Nexus7.2)', 'android_tests_n7_dbg_factory',
  scheduler='android_trigger_dbg', notify_on_missing=True)
F('android_tests_n7_dbg_factory', android().ChromiumWebRTCAndroidFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-chromium-tests-dbg',
      'build_url': android_dbg_archive,
      'perf_id': 'chromium-webrtc-dbg-android-nexus72',
      'show_perf_results': True,
      'test_platform': 'android',
    }))


def Update(config, active_master, c):
  helper.Update(c)
