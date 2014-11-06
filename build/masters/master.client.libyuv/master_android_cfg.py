# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='libyuv_android_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=[
          'Android Debug',
          'Android Release',
          'Android Clang Debug',
          'Android ARM64 Debug',
      ]),
  ])

  specs = [
    {'name': 'Android Debug'},
    {'name': 'Android Release'},
    {'name': 'Android Clang Debug', 'slavebuilddir': 'android_clang' },
    {'name': 'Android ARM64 Debug', 'slavebuilddir': 'android_arm64' },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('libyuv/libyuv'),
        'notify_on_missing': True,
        'category': 'android',
        'slavebuilddir': spec.get('slavebuilddir', 'android'),
      } for spec in specs
  ])
