# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_android_scheduler',
                            branch='trunk',
                            treeStableTimer=30,
                            builderNames=[
          'Android Builder',
          'Android Builder (dbg)',
          'Android Clang (dbg)',
          'Android ARM64 (dbg)',
          'Android GN',
          'Android GN (dbg)',
      ]),
      Triggerable(name='android_trigger_dbg', builderNames=[
          'Android Tests (KK Nexus5)(dbg)',
          'Android Tests (JB Nexus7.2)(dbg)',
      ]),
      Triggerable(name='android_trigger_rel', builderNames=[
          'Android Tests (KK Nexus5)',
          'Android Tests (JB Nexus7.2)',
      ]),
  ])

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {
      'name': 'Android Builder',
      'triggers': ['android_trigger_rel'],
    },
    {
      'name': 'Android Builder (dbg)',
      'triggers': ['android_trigger_dbg'],
    },
    {
      'name': 'Android Clang (dbg)',
      'slavebuilddir': 'android_clang',
    },
    {
      'name': 'Android ARM64 (dbg)',
      'slavebuilddir': 'android_arm64',
    },
    {
      'name': 'Android GN',
      'slavebuilddir': 'android_gn',
    },
    {
      'name': 'Android GN (dbg)',
      'slavebuilddir': 'android_gn',
    },
    {'name': 'Android Tests (KK Nexus5)(dbg)'},
    {'name': 'Android Tests (JB Nexus7.2)(dbg)'},
    {'name': 'Android Tests (KK Nexus5)'},
    {'name': 'Android Tests (JB Nexus7.2)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone',
                                           triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': 'android',
        'slavebuilddir': spec.get('slavebuilddir', 'android'),
      } for spec in specs
  ])
