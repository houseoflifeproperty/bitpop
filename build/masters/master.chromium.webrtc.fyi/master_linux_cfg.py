# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  buildernames_list = [
      'Linux',
      'Linux GN',
      'Linux GN (dbg)',
  ]
  c['schedulers'].extend([
      SingleBranchScheduler(name='linux_webrtc_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=buildernames_list),
      Periodic(name='linux_periodic_scheduler',
               periodicBuildTimer=60*60,
               builderNames=buildernames_list),
  ])
  specs = [
    {'name': 'Linux'},
    {
       'name': 'Linux GN',
       'slavebuilddir': 'linux_gn',
    },
    {
      'name': 'Linux GN (dbg)',
      'slavebuilddir': 'linux_gn',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/chromium'),
        'category': 'linux',
        'notify_on_missing': True,
        'slavebuilddir': spec.get('slavebuilddir', 'linux'),
      } for spec in specs
  ])
