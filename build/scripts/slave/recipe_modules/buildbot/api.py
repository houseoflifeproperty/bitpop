# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class BuildbotApi(recipe_api.RecipeApi):
  def prep(self):
    """Prepatory steps for buildbot based recipes."""
    # TODO(iannucci): Also do taskkill?
    self.m.python(
      'cleanup temp',
      self.m.path['build'].join('scripts', 'slave', 'cleanup_temp.py')
    )

  def copy_parent_got_revision_to_got_revision(self):
    """Returns a step which copies the 'parent_got_revision' build property
    to the 'got_revision' build property. This is needed for recipes which
    use isolates for testing and which skip the src/ checkout."""

    result = self.m.python.inline(
      'copy parent_got_revision to got_revision',
      'exit()')
    result.presentation.properties['got_revision'] = (
        self.m.properties['parent_got_revision'])
