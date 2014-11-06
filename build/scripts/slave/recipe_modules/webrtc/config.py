# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Single, Static, BadConf
from slave.recipe_config_types import Path


def BaseConfig(PERF_ID=None, PERF_CONFIG=None, **_kwargs):
  return ConfigGroup(
    PERF_ID = Static(PERF_ID),
    PERF_CONFIG = Static(PERF_CONFIG),
  )

VAR_TEST_MAP = {
  'PERF_ID': (None, 'perf-id'),
  'PERF_CONFIG': (None, '{}', '{"a_default_rev": "r_webrtc_rev"}'),
}

def TEST_NAME_FORMAT(kwargs):
  return 'webrtc'

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

@config_ctx()
def webrtc(c):
  pass

@config_ctx()
def webrtc_clang(c):
  pass

@config_ctx()
def webrtc_asan(c):
  pass

@config_ctx()
def webrtc_android(c):
  pass

@config_ctx()
def webrtc_android_clang(c):
  pass

@config_ctx()
def webrtc_ios(c):
  pass

# Only exists to be able to set the PERF_ID and PERF_CONFIG configurations.
@config_ctx()
def chromium(c):
  pass
