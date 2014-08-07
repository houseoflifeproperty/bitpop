# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  buildernames_list = ['Win Builder']
  c['schedulers'].extend([
      SingleBranchScheduler(name='win_webrtc_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=buildernames_list),
      Periodic(name='win_periodic_scheduler',
               periodicBuildTimer=4*60*60,
               builderNames=buildernames_list),
      Triggerable(name='win_rel_trigger', builderNames=[
          'WinXP Tester',
          'Win7 Tester',
      ]),
  ])
  specs = [
    {
      'name': 'Win Builder',
      'triggers': ['win_rel_trigger'],
    },
    {'name': 'WinXP Tester'},
    {'name': 'Win7 Tester'},
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
