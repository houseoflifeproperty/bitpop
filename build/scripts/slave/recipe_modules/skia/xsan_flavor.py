# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Utils for running under *SAN"""


import default_flavor


class XSanFlavorUtils(default_flavor.DefaultFlavorUtils):
  def __init__(self, *args, **kwargs):
    super(XSanFlavorUtils, self).__init__(*args, **kwargs)
    self._sanitizer = {
      'ASAN': 'address',
      'TSAN': 'thread',
    }[self._skia_api.c.builder_cfg['extra_config']]

  def compile(self, target):
    env = {}
    env.update(self._skia_api.c.gyp_env.as_jsonish())
    cmd = [self._skia_api.m.path['checkout'].join('tools', 'xsan_build'),
           self._sanitizer, target,
           'BUILDTYPE=%s' % self._skia_api.c.configuration]
    self._skia_api.m.step('build %s' % target, cmd, env=env,
                          cwd=self._skia_api.m.path['checkout'])

  def step(self, name, cmd, **kwargs):
    """Wrapper for the Step API; runs a step as appropriate for this flavor."""
    env = {}
    env['ASAN_OPTIONS'] = 'detect_leaks=0'
    tsan_suppressions = self._skia_api.m.path['checkout'].join('tools',
                                                               'tsan.supp')
    env['TSAN_OPTIONS'] = 'suppressions=%s' % tsan_suppressions
    path_to_app = self._skia_api.m.path['checkout'].join(
        'out', self._skia_api.c.configuration, cmd[0])
    new_cmd = [path_to_app]
    new_cmd.extend(cmd[1:])
    return self._skia_api.m.step(name, new_cmd, **kwargs)

