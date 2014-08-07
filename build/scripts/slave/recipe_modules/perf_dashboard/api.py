# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class PerfDashboardApi(recipe_api.RecipeApi):
  """Provides steps to take a list of perf points and post them to the
  Chromium Perf Dashboard.  Can also use the test url for testing purposes."""

  def get_skeleton_point(self, test, revision, value):
    # TODO: masterid is really mastername
    assert(test != '')
    assert(revision != '')
    assert(value != '')
    return {
      "master": self.m.properties['mastername'],
      "bot" : self.m.properties['slavename'],
      "test" : test,
      "revision" : revision,
      "value" : value,
      "masterid" : self.m.properties['mastername'],
      "buildername" : self.m.properties['buildername'],
      "buildnumber" : self.m.properties['buildnumber']
    }
  
  def set_default_config(self):
    """If in golo, use real perf server, otherwise use testing perf server."""
    if self.m.properties.get('use_mirror', True):  # We're on a bot
      self.set_config('production')
    else:
      self.set_config('testing')
  
  def post(self, data):
    """Takes a data object which can be jsonified and posts it to url."""
    yield self.m.python(
      name="perf dashboard post",
      script=self.resource('post_json.py'),
      stdin=self.m.json.input({
        'url' : self.c.url,
        'data' : data
      }))
