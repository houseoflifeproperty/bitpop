# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import default_flavor


"""Utils for building for and running tests on ChromeOS."""


def board_from_builder_dict(builder_dict):
  if 'CrOS' in builder_dict.get('extra_config', ''):
    if 'Alex' in builder_dict['extra_config']:
      return 'x86-alex'
    if 'Link' in builder_dict['extra_config']:
      return 'link'
    if 'Daisy' in builder_dict['extra_config']:
      return 'daisy'
  elif builder_dict['os'] == 'ChromeOS':
    return {
      'Alex': 'x86-alex',
      'Link': 'link',
      'Daisy': 'daisy',
    }[builder_dict['model']]
  # pragma: no cover
  raise Exception('No board found for builder: %s' % builder_cfg)


class ChromeOSFlavorUtils(default_flavor.DefaultFlavorUtils):
  def __init__(self, skia_api):
    super(ChromeOSFlavorUtils, self).__init__(skia_api)
    self.board = board_from_builder_dict(self._skia_api.c.builder_cfg)

  def compile(self, target):
    """Build the given target."""
    env = {}
    env.update(self._skia_api.c.gyp_env.as_jsonish())
    skia_dir = self._skia_api.m.path['checkout']
    cmd = [skia_dir.join('platform_tools', 'chromeos', 'bin', 'chromeos_make'),
           '-d', self.board,
           target,
           'BUILDTYPE=%s' % self._skia_api.c.configuration]
    self._skia_api.m.step('build %s' % target, cmd, cwd=skia_dir, env=env)

