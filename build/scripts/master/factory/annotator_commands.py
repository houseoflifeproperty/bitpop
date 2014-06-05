# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities to add commands to a buildbot factory.

This is based on commands.py and adds annotator-specific commands.
"""


from master import chromium_step
from master.factory import commands


class AnnotatorCommands(commands.FactoryCommands):
  """Encapsulates methods to add annotator commands to a factory."""

  def __init__(self, factory=None):
    self._call_counts = {}
    # Set self._script_dir and self._python, among other things.
    commands.FactoryCommands.__init__(self, factory)

  def AddAnnotatedScript(self, factory_properties, timeout, max_time):
    call_count = self._call_counts.setdefault('AddAnnotatedScript', 0)
    if call_count != 0:
      raise Exception("AnnotatorCommands.AddAnnotatedScript called twice.")
    self._call_counts['AddAnnotatedScript'] += 1
    factory_properties = factory_properties or {}
    runner = self.PathJoin(self._script_dir, 'annotated_run.py')
    cmd = [self._python, '-u', runner]
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='steps',
                          description='running steps via annotated script',
                          timeout=timeout,
                          maxTime=max_time,
                          haltOnFailure=True,
                          command=cmd)
