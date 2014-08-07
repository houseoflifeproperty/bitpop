# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_test_api

class IsolateTestApi(recipe_test_api.RecipeTestApi):
  def output_json(self, targets=None):
    """Mocked output of find_isolated_tests.py script.

    Deterministically synthesizes json.output test data for the given targets.
    If |targets| is None, will emit test data with some dummy targets instead,
    emulating find_isolated_tests.py finding some files.
    """
    if targets is None:
      targets = ['dummy_target_1', 'dummy_target_2']
    return self.m.json.output(dict(
        (target, '[dummy hash for %s]' % target) for target in targets))
