# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Single

def BaseConfig(**_kwargs):
  return ConfigGroup(
    url = Single(basestring)
  )

config_ctx = config_item_context(BaseConfig, {}, 'basic')

@config_ctx()
def production(c):
  c.url = "https://chromeperf.appspot.com"
  
@config_ctx()
def testing(c):
  c.url = "https://chrome-perf.googleplex.com"
