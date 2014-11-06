# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.chromium_android import CONFIG_CTX

# This file only exists to get the BUILD_CONFIG set for the chromium_android
# recipe module for the recipes using it.

@CONFIG_CTX()
def webrtc_android(c):
  pass

@CONFIG_CTX()
def webrtc_android_clang(c):
  pass

@CONFIG_CTX()
def chromium(c):
  pass
