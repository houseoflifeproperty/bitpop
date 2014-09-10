# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import default_flavor


"""Utils for building for and running tests in NaCl."""


DEFAULT_NACL_SDK_ROOT = '/home/chrome-bot/nacl_sdk/pepper_32'


class NaClFlavorUtils(default_flavor.DefaultFlavorUtils):
  def compile(self, target):
    """Build the given target."""
    env = {}
    env['NACL_SDK_ROOT'] = DEFAULT_NACL_SDK_ROOT
    skia_dir = self._skia_api.m.path['checkout']
    cmd = [skia_dir.join('platform_tools', 'nacl', 'nacl_make'),
           target,
           'BUILDTYPE=%s' % self._skia_api.c.configuration]
    if self._skia_api.ccache:
      cmd.append('--use-ccache')
    self._skia_api.m.step('build %s' % target, cmd, env=env, cwd=skia_dir)

