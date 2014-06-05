# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup, Single, List
from slave.recipe_config import Static
from slave.recipe_config_types import Path

def BaseConfig(USE_MIRROR=False):
  chromium_in_android_subpath = ('external', 'chromium_org')
  build_path = Path('[SLAVE_BUILD]', 'android-src')

  return ConfigGroup(
    lunch_flavor = Single(basestring),
    repo = ConfigGroup(
      url = Single(basestring),
      branch = Single(basestring),
      sync_flags = List(basestring),
    ),
    USE_MIRROR = Static(bool(USE_MIRROR)),
    # If present causes the sync step to use the specified manifest instead of
    # the one associated with the repo.branch.
    sync_manifest_override = Single(Path, required=False),

    # Path stuff
    chromium_in_android_subpath = Static('/'.join(chromium_in_android_subpath)),
    build_path = Static(build_path),
    slave_chromium_in_android_path = Static(
      build_path.join(*chromium_in_android_subpath)),
    slave_android_out_path = Static(build_path.join('out')),
  )

config_ctx = config_item_context(
  BaseConfig,
  {'USE_MIRROR': (False,)},
  'android')

@config_ctx()
def AOSP(c):
  c.lunch_flavor = 'full-eng'
  c.repo.url = 'https://android.googlesource.com/platform/manifest'
  c.repo.branch = 'android-4.4_r1'
  c.repo.sync_flags = ['-j6', '-d', '-f']

@config_ctx(includes=['AOSP'])
def AOSP_webview(c):
  c.sync_manifest_override = Path('[CHECKOUT]', 'android_webview', 'buildbot',
                                  'aosp_manifest.xml')
