# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Inherits buildbot.process.base.Build to add BuildFactory inherited
properties."""

from buildbot.process import base


class Build(base.Build):
  """Build class that inherits the BuildFactory properties."""

  def __init__(self, request, factory_properties):
    self.result = None
    base.Build.__init__(self, request)
    self._factory_properties = factory_properties

  def setupProperties(self):
    """Adds BuildFactory inherited properties."""
    base.Build.setupProperties(self)
    self.getProperties().updateFromProperties(self._factory_properties)
