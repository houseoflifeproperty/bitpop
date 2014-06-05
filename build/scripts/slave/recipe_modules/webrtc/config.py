# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Single, Static, BadConf
from slave.recipe_config_types import Path


def BaseConfig(**_kwargs):
  return ConfigGroup(
    patch_root_dir = Single(Path, required=False, empty_val=Path('[CHECKOUT]')),

    # Allow manipulating patches for try jobs.
    patch_filter_script = Single(Path, required=False),
    patch_path_filter = Single(basestring, required=False),
    patch_strip_level = Single(int, required=False, empty_val=0),
  )

VAR_TEST_MAP = {
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
def webrtc_android(c):
  pass


@config_ctx()
def webrtc_android_clang(c):
  pass


@config_ctx()
def webrtc_android_apk(c):
  """ Build WebRTC native tests for Android as APKs."""
  pass


@config_ctx()
def webrtc_android_apk_try_builder(c):
  """ Configure patch manipulation for WebRTC Android APK trybots."""
  c.patch_root_dir = Path('[CHECKOUT]', 'third_party', 'webrtc')
  c.patch_filter_script = Path('[BUILD]', 'scripts', 'slave',
                               'patch_path_filter.py')
  c.patch_path_filter = 'webrtc/'
  c.patch_strip_level = 1


@config_ctx()
def webrtc_ios(c):
  pass

