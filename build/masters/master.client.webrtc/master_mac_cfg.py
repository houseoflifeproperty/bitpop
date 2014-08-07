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

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {'name': 'Mac32 Debug', 'slavebuilddir': 'mac32'},
    {'name': 'Mac32 Release', 'slavebuilddir': 'mac32'},
    {'name': 'Mac64 Debug', 'slavebuilddir': 'mac64'},
    {'name': 'Mac64 Release', 'slavebuilddir': 'mac64'},
    {
      'name': 'Mac32 Release [large tests]',
      'category': 'compile|baremetal',
      'slavebuilddir': 'mac_baremetal',
    },
    {'name': 'Mac Asan', 'slavebuilddir': 'mac_asan'},
    {'name': 'iOS Debug', 'slavebuilddir': 'ios'},
    {'name': 'iOS Release', 'slavebuilddir': 'ios'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': spec.get('category', 'compile|testers'),
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
