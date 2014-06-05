# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(_config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='linux_src',
                            branch='src',
                            treeStableTimer=60,
                            builderNames=[
          'Linux Builder',
          'Linux Builder (dbg)(32)',
          'Linux Builder (dbg)',
          'Linux Clang (dbg)',
          'Linux GN',
          'Linux GN (dbg)',
      ]),
      Triggerable(name='linux_rel_trigger', builderNames=[
          'Linux Tests',
          'Linux Sync',
      ]),
      Triggerable(name='linux_dbg_32_trigger', builderNames=[
          'Linux Tests (dbg)(1)(32)',
          'Linux Tests (dbg)(2)(32)',
      ]),
      Triggerable(name='linux_dbg_trigger', builderNames=[
          'Linux Tests (dbg)(1)',
          'Linux Tests (dbg)(2)',
      ]),
  ])
  specs = [
    {
      'name': 'Linux Builder',
      'triggers': ['linux_rel_trigger'],
    },
    {'name': 'Linux Tests'},
    {'name': 'Linux Sync'},
    {'name': 'Linux Builder (dbg)(32)', 'triggers': ['linux_dbg_32_trigger']},
    {'name': 'Linux Tests (dbg)(1)(32)'},
    {'name': 'Linux Tests (dbg)(2)(32)'},
    {'name': 'Linux Builder (dbg)', 'triggers': ['linux_dbg_trigger']},
    {'name': 'Linux Tests (dbg)(1)'},
    {'name': 'Linux Tests (dbg)(2)'},
    {'name': 'Linux Clang (dbg)'},
    {'name': 'Linux GN', 'recipe': 'chromium_gn'},
    {'name': 'Linux GN (dbg)', 'recipe': 'chromium_gn'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            spec.get('recipe', 'chromium'),
            factory_properties=spec.get('factory_properties'),
            triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '4linux',
      } for spec in specs
  ])
