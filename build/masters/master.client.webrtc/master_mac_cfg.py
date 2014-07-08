# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=[
          'Mac32 Debug',
          'Mac32 Release',
          'Mac64 Debug',
          'Mac64 Release',
          'Mac32 Release [large tests]',
          'Mac Asan',
          'iOS Debug',
          'iOS Release',
      ]),
  ])

  # Recipe based builders.
  specs = [
    {'name': 'Mac32 Debug', 'slavebuilddir': 'mac32'},
    {'name': 'Mac32 Release', 'slavebuilddir': 'mac32'},
    {'name': 'Mac64 Debug', 'slavebuilddir': 'mac64'},
    {'name': 'Mac64 Release', 'slavebuilddir': 'mac64'},
    {'name': 'Mac Asan', 'slavebuilddir': 'mac_asan'},
    {'name': 'iOS Debug', 'slavebuilddir': 'ios'},
    {'name': 'iOS Release', 'slavebuilddir': 'ios'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'compile|testers',
        'slavebuilddir': spec.get('slavebuilddir'),
      } for spec in specs
  ])

  # Builders not-yet-switched to recipes.
  from master.factory import webrtc_factory
  def mac():
    return webrtc_factory.WebRTCFactory('src/out', 'darwin')

  f_mac32_largetests = mac().WebRTCFactory(
      target='Release',
      options=['--compiler=goma-clang'],
      tests=[
        'audio_device_tests',
        'video_capture_tests',
        'vie_auto_test',
        'voe_auto_test',
        'webrtc_perf_tests',
      ],
      factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-mac-large-tests',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'perf_measuring_tests': ['vie_auto_test',
                                 'webrtc_perf_tests'],
        'custom_cmd_line_tests': ['vie_auto_test',
                                  'voe_auto_test'],
      })
  b_mac32_largetests = {
    'name': 'Mac32 Release [large tests]',
    'factory': f_mac32_largetests,
    'category': 'compile|baremetal',
    'auto_reboot' : True,
  }

  c['builders'].extend([
      b_mac32_largetests,
  ])
