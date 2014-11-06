# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=['Linux64 Debug (parallel)']),
  ])

  specs = [
    {
      'name': 'Linux64 Debug (parallel)',
      'slavebuilddir': 'linux',
    }
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
