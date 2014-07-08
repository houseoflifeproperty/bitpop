# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_windows_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=[
          'Win32 Debug',
          'Win32 Release',
          'Win64 Debug',
          'Win64 Release',
          'Win32 Release [large tests]',
          'Win DrMemory Light',
          'Win DrMemory Full',
          'Win SyzyASan',
      ]),
  ])

  # Recipe based builders.
  specs = [
    {'name': 'Win32 Debug'},
    {'name': 'Win32 Release'},
    {'name': 'Win64 Debug'},
    {'name': 'Win64 Release'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'compile|testers|windows',
        'slavebuilddir': 'win',
      } for spec in specs
  ])

  # Builders not-yet-switched to recipes.
  from master.factory import webrtc_factory
  def win():
    return webrtc_factory.WebRTCFactory('src/out', 'win32')

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
    'audio_device_tests',
    'video_capture_tests',
    'vie_auto_test',
    'voe_auto_test',
    'webrtc_perf_tests',
  ]

  options=['--compiler=goma']
  dr_memory_factory_properties = {
    'gclient_env': {'GYP_DEFINES': 'build_for_tool=drmemory'},
    'needs_drmemory': True,
  }

  f_win32_largetests = win().WebRTCFactory(
      target='Release',
      options=options,
      tests=baremetal_tests,
      factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-win-large-tests',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'perf_measuring_tests': ['vie_auto_test',
                                 'webrtc_perf_tests'],
        'custom_cmd_line_tests': ['vie_auto_test',
                                  'voe_auto_test'],
      })
  b_win32_largetests = {
    'name': 'Win32 Release [large tests]',
    'factory': f_win32_largetests,
    'category': 'compile|baremetal|windows',
    'slavebuilddir': 'win',
    'auto_reboot' : True,
  }

  f_win_drmemory_light = win().WebRTCFactory(
    target='Debug',
    options=options,
    tests=['drmemory_light_' + test for test in tests],
    factory_properties=dr_memory_factory_properties)
  b_win_drmemory_light = {
    'name': 'Win DrMemory Light',
    'factory': f_win_drmemory_light,
    'category': 'compile',
    'slavebuilddir': 'win-drmem',
    'auto_reboot' : True,
  }

  f_win_drmemory_full = win().WebRTCFactory(
    target='Debug',
    options=options,
    tests=['drmemory_full_' + test for test in tests],
    factory_properties=dr_memory_factory_properties)
  b_win_drmemory_full = {
    'name': 'Win DrMemory Full',
    'factory': f_win_drmemory_full,
    'category': 'compile',
    'slavebuilddir': 'win-drmem',
    'auto_reboot' : True,
  }

  f_win_syzy_asan = win().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests,
    factory_properties={
        'syzyasan': True,
        'gclient_env': {
            'GYP_DEFINES': ('syzyasan=1 win_z7=1 chromium_win_pch=0 '
                            'component=static_library'),
            'GYP_USE_SEPARATE_MSPDBSRV': '1',
        },
    })
  b_win_syzy_asan = {
    'name': 'Win SyzyASan',
    'factory': f_win_syzy_asan,
    'category': 'compile|testers|windows',
    'auto_reboot' : True,
  }

  c['builders'].extend([
      b_win32_largetests,
      b_win_drmemory_light,
      b_win_drmemory_full,
      b_win_syzy_asan,
   ])
