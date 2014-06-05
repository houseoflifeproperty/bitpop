# Copyright (c) 2014 The Chromium Authors. All Rights Reserved.
# Use of this code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_test_api

class AdbTestApi(recipe_test_api.RecipeTestApi):
  def device_list(self):
    return self.m.json.output(["014E1F310401C009"])
