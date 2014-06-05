# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def linux():
  return webrtc_factory.WebRTCFactory('src/out', 'linux2')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_linux_scheduler'
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

baremetal_tests = [
    'audio_e2e_test',
    'audioproc_perf',
    'isac_fixed_perf',
    'libjingle_peerconnection_java_unittest',
    'video_capture_tests',
    'vie_auto_test',
    'voe_auto_test',
    'webrtc_perf_tests',
]

options=['--compiler=goma']

defaults['category'] = 'linux'

B('Linux32 Debug', 'linux32_debug_factory', 'compile|testers', scheduler,
  slavebuilddir='linux32')
F('linux32_debug_factory', linux().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'},
    }))

B('Linux32 Release', 'linux32_release_factory', 'compile|testers', scheduler,
  slavebuilddir='linux32')
F('linux32_release_factory', linux().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'},
    }))

B('Linux64 Debug', 'linux64_debug_factory', 'compile|testers', scheduler,
  slavebuilddir='linux64')
F('linux64_debug_factory', linux().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
    }))

B('Linux64 Release', 'linux64_release_factory', 'compile|testers', scheduler,
  slavebuilddir='linux64')
F('linux64_release_factory', linux().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
    }))

B('Linux Clang', 'linux_clang_factory', 'compile|testers', scheduler)
F('linux_clang_factory', linux().WebRTCFactory(
    target='Debug',
    options=['--compiler=goma-clang'],
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {'GYP_DEFINES': 'clang=1'},
    }))

B('Linux Memcheck', 'linux_memcheck_factory', 'compile', scheduler)
F('linux_memcheck_factory', linux().WebRTCFactory(
    target='Release',
    options=options,
    tests=['memcheck_' + test for test in tests],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=memcheck'},
    }))

B('Linux Tsan', 'linux_tsan_factory', 'compile', scheduler)
F('linux_tsan_factory', linux().WebRTCFactory(
    target='Release',
    options=options,
    tests=['tsan_' + test for test in tests],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=memcheck'},
    }))

B('Linux Tsan v2', 'linux_tsan2_factory', 'compile', scheduler)
F('linux_tsan2_factory', linux().WebRTCFactory(
    target='Release',
    tests=tests,
    options=['--compiler=goma-clang'],
    factory_properties={
        'tsan': True,
        'tsan_suppressions_file':
            'src/tools/valgrind-webrtc/tsan_v2/suppressions.txt',
        'gclient_env': {
            'GYP_DEFINES': 'tsan=1 use_allocator=none release_extra_cflags=-g',
    }}))

B('Linux Asan', 'linux_asan_factory', 'compile|testers', scheduler)
F('linux_asan_factory', linux().WebRTCFactory(
    target='Release',
    options=['--compiler=goma-clang'],
    tests=tests,
    factory_properties={
        'asan': True,
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {
            'GYP_DEFINES': ('asan=1 release_extra_cflags=-g '
                            'use_allocator=none ')},
    }))

B('Linux64 Release [large tests]', 'linux_largetests_factory',
  'compile|baremetal', scheduler)
F('linux_largetests_factory', linux().WebRTCFactory(
    target='Release',
    options=options,
    tests=baremetal_tests,
    factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-linux-large-tests',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'perf_measuring_tests': ['audio_e2e_test',
                                 'audioproc_perf',
                                 'isac_fixed_perf',
                                 'vie_auto_test',
                                 'webrtc_perf_tests'],
        'custom_cmd_line_tests': ['audio_e2e_test',
                                  'audioproc_perf',
                                  'isac_fixed_perf',
                                  'libjingle_peerconnection_java_unittest',
                                  'vie_auto_test',
                                  'voe_auto_test'],
    }))

# ChromeOS.
B('Chrome OS', 'chromeos_factory', 'compile|testers', scheduler)
F('chromeos_factory', linux().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'chromeos=1'},
    }))


def Update(c):
  helper.Update(c)
