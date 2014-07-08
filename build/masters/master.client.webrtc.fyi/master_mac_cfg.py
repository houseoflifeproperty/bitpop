# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}

def mac():
  return webrtc_factory.WebRTCFactory('src/out', 'darwin')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_mac_scheduler'
S(scheduler, branch='trunk', treeStableTimer=0)

tests = [
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
    'modules_tests',
    'modules_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'video_engine_tests',
    'voice_engine_unittests',
]

defaults['category'] = 'mac'

valgrind_mac_factory_properties = {
    'needs_valgrind': True,
    'gclient_env': {
        'GYP_DEFINES': 'build_for_tool=memcheck target_arch=ia32'
    }
}

B('Mac 10.6 Memcheck', 'mac_memcheck_factory', scheduler=scheduler)
F('mac_memcheck_factory', mac().WebRTCFactory(
    target='Debug',
    tests=['memcheck_' + test for test in tests],
    factory_properties=valgrind_mac_factory_properties))

B('Mac 10.6 TSan', 'mac_tsan_factory', scheduler=scheduler)
F('mac_tsan_factory', mac().WebRTCFactory(
    target='Debug',
    tests=['tsan_' + test for test in tests],
    factory_properties=valgrind_mac_factory_properties))


def Update(c):
  helper.Update(c)
