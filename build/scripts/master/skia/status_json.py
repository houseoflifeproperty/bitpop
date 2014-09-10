# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Utilities for adding JSON status targets."""


from buildbot.status.web import status_json
from common.skia import builder_name_schema


class JsonStatusHelper(object):
  """Allows the user to add JSON status targets to the root JsonStatusResource.

  This class:
    - Monkeypatches buildbot.status.web.status_json.JsonStatusResource.__init__.
    - Is intended to be used in master.cfg files before the JSON status targets
      are instantiated.
    - Is NOT thread-safe, however any number of JsonStatusHelpers may be used
      sequentially or simultaneously within the same thread.
  """
  def __init__(self):
    self.children = None

  def putChild(self, name, classtype, *args, **kwargs):
    self.children.append((name, classtype, args, kwargs))

  def __enter__(self):
    self.children = []
    return self

  def __exit__(self, _type, _value, _traceback):
    JsonStatusResource__init__old = status_json.JsonStatusResource.__init__
    helper = self
    def JsonStatusResource__init__(self, status):
      JsonStatusResource__init__old(self, status)
      for name, classtype, args, kwargs in helper.children:
        self.putChild(name, classtype(status, *args, **kwargs))
    status_json.JsonStatusResource.__init__ = JsonStatusResource__init__


class TryBuildersJsonResource(status_json.JsonResource):
  """Clone of buildbot.status.web.status_json.BuildersJsonResource.

  We add filtering to display only the try builders.
  """
  help = """List of all the try builders defined on a master."""
  pageTitle = 'Builders'

  def __init__(self, status):
    status_json.JsonResource.__init__(self, status)
    for builder_name in self.status.getBuilderNames():
      if builder_name_schema.IsTrybot(builder_name):
        self.putChild(builder_name,
                      status_json.BuilderJsonResource(
                          status, status.getBuilder(builder_name)))
