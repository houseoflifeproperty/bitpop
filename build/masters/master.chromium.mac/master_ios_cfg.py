# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='ios',
                            branch='src',
                            treeStableTimer=60,
                            builderNames=[
          'iOS Device',
          'iOS Simulator (dbg)',
          'iOS Device (ninja)',
      ]),
  ])
  specs = [
    {'name': 'iOS Device'},
    {'name': 'iOS Simulator (dbg)'},
    {'name': 'iOS Device (ninja)'},
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
