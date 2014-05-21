# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, category, custom_deps_list=None):
  def win():
    return webrtc_factory.WebRTCFactory('src/build', 'win32', svn_url,
                                        branch, custom_deps_list)
  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_%s_win_scheduler' % category
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

  project = r'..\webrtc.sln'
  factory_prop = {
      'gclient_env': {'GYP_GENERATOR_FLAGS': 'msvs_error_on_missing_sources=1'}
  }

  defaults['category'] = category

  B('Win32Debug', 'win32_debug_factory', scheduler=scheduler)
  F('win32_debug_factory', win().WebRTCFactory(
      target='Debug',
      project=project,
      tests=normal_tests,
      factory_properties=factory_prop))
  B('Win32Release', 'win32_release_factory', scheduler=scheduler)
  F('win32_release_factory', win().WebRTCFactory(
      target='Release',
      project=project,
      tests=normal_tests,
      factory_properties=factory_prop))

  helper.Update(c)
