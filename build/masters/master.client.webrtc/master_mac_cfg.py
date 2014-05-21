# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, category, custom_deps_list=None):
  def mac():
    return webrtc_factory.WebRTCFactory('src/build', 'darwin', svn_url,
                                        branch, custom_deps_list)
  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_%s_mac_scheduler' % category
  S(scheduler, branch=branch, treeStableTimer=0)

  normal_tests = ['audio_coding_module_test',
                  'audio_coding_unittests',
                  'audioproc_unittest',
                  'bitrate_controller_unittests',
                  'common_video_unittests',
                  'media_file_unittests',
                  'metrics_unittests',
                  'neteq_unittests',
                  'resampler_unittests',
                  'rtp_rtcp_unittests',
                  'signal_processing_unittests',
                  'system_wrappers_unittests',
                  'remote_bitrate_estimator_unittests',
                  'test_fec',
                  'test_support_unittests',
                  'udp_transport_unittests',
                  'vad_unittests',
                  'video_coding_unittests',
                  'video_engine_core_unittests',
                  'video_processing_unittests',
                  'voice_engine_unittests',
                  'vp8_integrationtests',
                  'vp8_unittests',
                  'webrtc_utility_unittests',]

  asan_disabled_tests = [
      'audio_coding_module_test', # Issue 281
      'neteq_unittests',          # Issue 282
  ]
  asan_tests = filter(lambda test: test not in asan_disabled_tests,
                      normal_tests)
  options = ['--', '-project', '../webrtc.xcodeproj']

  defaults['category'] = category

  B('Mac32Debug', 'mac_debug_factory', scheduler=scheduler)
  F('mac_debug_factory', mac().WebRTCFactory(
      target='Debug',
      options=options,
      tests=normal_tests))
  B('Mac32Release', 'mac_release_factory', scheduler=scheduler)
  F('mac_release_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=normal_tests))
  B('MacAsan', 'mac_asan_factory', scheduler=scheduler)
  F('mac_asan_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=asan_tests,
      factory_properties={'asan': True,
                          'gclient_env':
                          {'GYP_DEFINES': ('asan=1'
                                           ' release_extra_cflags=-g '
                                           ' linux_use_tcmalloc=0 ')}}))
  helper.Update(c)
