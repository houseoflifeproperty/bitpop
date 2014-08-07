# Copyright 2013 The Chromium Authors. All rights reserved.
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
                            builderNames=['Win Tsan']),
  ])

  specs = [
    {'name': 'Win Tsan', 'slavebuilddir': 'win_tsan'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'win',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
