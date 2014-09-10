# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  buildernames_list = [
      'Android Builder (dbg)',
      'Android GN',
      'Android GN (dbg)',
  ]
  c['schedulers'].extend([
      SingleBranchScheduler(name='android_webrtc_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=buildernames_list),
      Periodic(name='android_periodic_scheduler',
               periodicBuildTimer=30*60,
               builderNames=buildernames_list),
      Triggerable(name='android_trigger_dbg', builderNames=[
          'Android Tests (dbg) (KK Nexus5)',
          'Android Tests (dbg) (JB Nexus7.2)',
      ]),
  ])

  specs = [
    {
      'name': 'Android Builder (dbg)',
      'triggers': ['android_trigger_dbg'],
    },
    {'name': 'Android Tests (dbg) (KK Nexus5)'},
    {'name': 'Android Tests (dbg) (JB Nexus7.2)'},
    {
      'name': 'Android GN',
      'slavebuilddir': 'android_gn',
    },
    {
      'name': 'Android GN (dbg)',
      'slavebuilddir': 'android_gn',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            'webrtc/chromium',
            triggers=spec.get('triggers')),
        'category': 'android',
        'notify_on_missing': True,
        'slavebuilddir': spec.get('slavebuilddir', 'android'),
      } for spec in specs
  ])
