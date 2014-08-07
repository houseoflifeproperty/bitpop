# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='win_rel_scheduler',
                            branch='src',
                            treeStableTimer=60,
                            builderNames=['Win Builder']),
      Triggerable(name='win_rel_trigger', builderNames=[
          'WinXP Tester',
          'Win7 Tester',
          'Win8 Tester',
      ]),
  ])
  specs = [
    {
      'name': 'Win Builder',
      'triggers': ['win_rel_trigger'],
    },
    {'name': 'WinXP Tester'},
    {'name': 'Win7 Tester'},
    {'name': 'Win8 Tester'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            'webrtc/chromium',
            triggers=spec.get('triggers')),
        'category': 'win',
        'notify_on_missing': True,
      } for spec in specs
  ])
