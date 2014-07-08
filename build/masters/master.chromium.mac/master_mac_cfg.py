# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='mac_src',
                            branch='src',
                            treeStableTimer=60,
                            builderNames=[
          'Mac Builder',
          'Mac Builder (dbg)',
      ]),
      Triggerable(name='mac_rel_trigger', builderNames=[
          'Mac10.6 Tests (1)',
          'Mac10.6 Tests (2)',
          'Mac10.6 Tests (3)',
          'Mac10.7 Tests (1)',
          'Mac10.7 Tests (2)',
          'Mac10.7 Tests (3)',
          'Mac10.6 Sync',
      ]),
      Triggerable(name='mac_dbg_trigger', builderNames=[
          'Mac 10.6 Tests (dbg)(1)',
          'Mac 10.6 Tests (dbg)(2)',
          'Mac 10.6 Tests (dbg)(3)',
          'Mac 10.6 Tests (dbg)(4)',
          'Mac 10.7 Tests (dbg)(1)',
          'Mac 10.7 Tests (dbg)(2)',
          'Mac 10.7 Tests (dbg)(3)',
          'Mac 10.7 Tests (dbg)(4)',
      ]),
  ])
  specs = [
    {
      'name': 'Mac Builder',
      'triggers': ['mac_rel_trigger'],
    },
    {'name': 'Mac10.6 Tests (1)'},
    {'name': 'Mac10.6 Tests (2)'},
    {'name': 'Mac10.6 Tests (3)'},
    {'name': 'Mac10.7 Tests (1)'},
    {'name': 'Mac10.7 Tests (2)'},
    {'name': 'Mac10.7 Tests (3)'},
    {'name': 'Mac10.6 Sync'},
    {
      'name': 'Mac Builder (dbg)',
      'triggers': ['mac_dbg_trigger'],
    },
    {'name': 'Mac 10.6 Tests (dbg)(1)'},
    {'name': 'Mac 10.6 Tests (dbg)(2)'},
    {'name': 'Mac 10.6 Tests (dbg)(3)'},
    {'name': 'Mac 10.6 Tests (dbg)(4)'},
    {'name': 'Mac 10.7 Tests (dbg)(1)'},
    {'name': 'Mac 10.7 Tests (dbg)(2)'},
    {'name': 'Mac 10.7 Tests (dbg)(3)'},
    {'name': 'Mac 10.7 Tests (dbg)(4)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            'chromium',
            factory_properties=spec.get('factory_properties'),
            triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '3mac',
      } for spec in specs
  ])
