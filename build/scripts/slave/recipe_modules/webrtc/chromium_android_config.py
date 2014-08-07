# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.chromium_android import CONFIG_CTX


@CONFIG_CTX()
def webrtc_android_apk(c):
  pass

# Only exists to get the BUILD_CONFIG set for the chromium_android config.
@CONFIG_CTX()
def chromium(c):
  pass
