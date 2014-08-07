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

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {'name': 'Win32 Debug'},
    {'name': 'Win32 Release'},
    {'name': 'Win64 Debug'},
    {'name': 'Win64 Release'},
    {
      'name': 'Win32 Release [large tests]',
      'category': 'compile|baremetal|windows',
      'slavebuilddir': 'win_baremetal',
    },
    {
      'name': 'Win DrMemory Light',
      'category': 'compile',
      'slavebuilddir': 'win-drmem',
    },
    {
      'name': 'Win DrMemory Full',
      'category': 'compile',
      'slavebuilddir': 'win-drmem',
    },
    {'name': 'Win SyzyASan', 'slavebuilddir': 'win-syzyasan'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': spec.get('category', 'compile|testers|windows'),
        'slavebuilddir': spec.get('slavebuilddir', 'win'),
      } for spec in specs
  ])
