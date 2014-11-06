# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class LibyuvApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(LibyuvApi, self).__init__(**kwargs)
