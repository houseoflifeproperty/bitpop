# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='mac_rel_scheduler',
                            branch='src',
                            treeStableTimer=60,
                            builderNames=['Mac Builder']),
      Triggerable(name='mac_rel_trigger',
                  builderNames=['Mac Tester']),
  ])
  specs = [
    {
      'name': 'Mac Builder',
      'triggers': ['mac_rel_trigger'],
    },
    {'name': 'Mac Tester'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            'webrtc/chromium',
            triggers=spec.get('triggers')),
        'category': 'mac',
        'notify_on_missing': True,
      } for spec in specs
  ])
