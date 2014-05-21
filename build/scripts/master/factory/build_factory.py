# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Inherits buildbot.process.factory.BuildFactory to add BuildFactory inherited
properties."""

from buildbot.process import factory
from buildbot.process import properties

from master.factory import build


class BuildFactory(factory.BuildFactory):
  """A Build Factory affected by properties.

  The properties will affect which steps are run for each new Build produced.
  The generated Build object will inherit the factory properties.
  """
  # Overide the Build class to active the property inheritance.
  buildClass = build.Build

  def __init__(self, build_factory_properties=None, steps=None):
    factory.BuildFactory.__init__(self, steps)
    self.properties = properties.Properties()
    if build_factory_properties:
      self.properties.update(build_factory_properties, 'BuildFactory')

  def newBuild(self, request):
    """Creates a new buildClass instance and gives it our properties."""
    b = self.buildClass(request, self.properties)
    b.useProgress = self.useProgress
    b.setStepFactories(self.steps)
    return b
