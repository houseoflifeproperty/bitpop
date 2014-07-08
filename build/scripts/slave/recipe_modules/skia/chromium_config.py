# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config_types import Path
from RECIPE_MODULES.chromium import CONFIG_CTX


@CONFIG_CTX()
def skia(c):
  c.build_config_fs = c.BUILD_CONFIG
  c.build_dir = Path('[CHECKOUT]', 'out')
