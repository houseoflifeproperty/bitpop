# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def win():
  return webrtc_factory.WebRTCFactory('src/out', 'win32')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_win_scheduler'
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

options=['--compiler=goma']

defaults['category'] = 'win'

B('Win Tsan', 'win_tsan_factory', scheduler=scheduler)
F('win_tsan_factory', win().WebRTCFactory(
    target='Debug',
    options=options,
    tests=['tsan_' + test for test in tests],
    factory_properties={
        'needs_tsan_win': True,
        'gclient_env': { 'GYP_DEFINES' : 'build_for_tool=tsan' },
    }))


def Update(c):
  helper.Update(c)
