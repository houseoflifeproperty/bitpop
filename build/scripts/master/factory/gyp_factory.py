# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""BuildFactory creator to run GYP tests."""

import os

from master import chromium_step

import config
from master.factory import gclient_factory


class GYPFactory(gclient_factory.GClientFactory):
  svn_url = config.Master.gyp_trunk_url

  def __init__(self, build_dir, **kw):
    main = gclient_factory.GClientSolution(self.svn_url)
    super(GYPFactory, self).__init__(build_dir, [main], **kw)

  def GYPFactory(self):
    f = self.BaseFactory()
    cmd = [
        'python',
        os.path.join(self._build_dir, 'buildbot', 'buildbot_run.py'),
    ]
    f.addStep(chromium_step.AnnotatedCommand,
              name='annotate',
              description='annotate',
              command=cmd)
    return f
