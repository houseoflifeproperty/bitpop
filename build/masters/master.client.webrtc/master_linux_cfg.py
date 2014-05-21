# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, category, custom_deps_list=None):
  def linux():
    return webrtc_factory.WebRTCFactory('src/build', 'linux2', svn_url,
                                        branch, custom_deps_list)
  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_%s_linux_scheduler' % category
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

  memcheck_disabled_tests = [
      'audio_coding_module_test', # Issue 270
      'test_fec',                 # Too slow for memcheck
  ]
  memcheck_tests = filter(lambda test: test not in memcheck_disabled_tests,
                          normal_tests)
  tsan_disabled_tests = [
      'audio_coding_module_test',   # Issue 283
      'audioproc_unittest',         # Issue 299
      'system_wrappers_unittests',  # Issue 300
      'video_processing_unittests', # Issue 303
      'test_fec',                   # Too slow for TSAN
  ]
  tsan_tests = filter(lambda test: test not in tsan_disabled_tests,
                      normal_tests)
  asan_disabled_tests = [
      'audio_coding_module_test', # Issue 281
      'neteq_unittests',          # Issue 282
  ]
  asan_tests = filter(lambda test: test not in asan_disabled_tests,
                      normal_tests)

  defaults['category'] = category

  B('Linux32Debug', 'linux32_debug_factory', scheduler=scheduler)
  F('linux32_debug_factory', linux().WebRTCFactory(
      target='Debug',
      tests=normal_tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))
  B('Linux32Release', 'linux32_release_factory', scheduler=scheduler)
  F('linux32_release_factory', linux().WebRTCFactory(
      target='Release',
      tests=normal_tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))

  B('Linux64Debug', 'linux64_debug_factory', scheduler=scheduler)
  F('linux64_debug_factory', linux().WebRTCFactory(
      target='Debug',
      tests=normal_tests))
  B('Linux64Release', 'linux64_release_factory', scheduler=scheduler)
  F('linux64_release_factory', linux().WebRTCFactory(
      target='Release',
      tests=normal_tests))

  B('LinuxClang', 'linux_clang_factory', scheduler=scheduler)
  F('linux_clang_factory', linux().WebRTCFactory(
      target='Debug',
      tests=normal_tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'clang=1'}}))

  B('LinuxMemcheck', 'linux_memcheck_factory', scheduler=scheduler)
  F('linux_memcheck_factory', linux().WebRTCFactory(
      target='Release',
      tests=['memcheck_' + test for test in memcheck_tests],
      factory_properties={'needs_valgrind': True,
                          'gclient_env':
                          {'GYP_DEFINES': 'build_for_tool=memcheck'}}))
  B('LinuxTsan', 'linux_tsan_factory', scheduler=scheduler)
  F('linux_tsan_factory', linux().WebRTCFactory(
      target='Release',
      tests=['tsan_' + test for test in tsan_tests],
      factory_properties={'needs_valgrind': True,
                          'gclient_env':
                          {'GYP_DEFINES': 'build_for_tool=tsan'}}))
  B('LinuxAsan', 'linux_asan_factory', scheduler=scheduler)
  F('linux_asan_factory', linux().WebRTCFactory(
      target='Release',
      tests=asan_tests,
      factory_properties={'asan': True,
                          'gclient_env':
                          {'GYP_DEFINES': ('asan=1 release_extra_cflags=-g '
                                           ' linux_use_tcmalloc=0 ')}}))

  # ChromeOS.
  B('CrOS', 'chromeos_factory', scheduler=scheduler)
  F('chromeos_factory', linux().WebRTCFactory(
      target='Debug',
      tests=normal_tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'chromeos=1'}}))

  helper.Update(c)
