# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import default_flavor


"""Android flavor utils, used for building for and running tests on Android."""


DEFAULT_ANDROID_SDK_ROOT = '/home/chrome-bot/android-sdk-linux'


def device_from_builder_dict(builder_dict):
  """Given a builder name dictionary, return an Android device name."""
  if 'Android' in builder_dict.get('extra_config', ''):
    if 'NoThumb' in builder_dict['extra_config']:
      return 'arm_v7'
    if 'NoNeon' in builder_dict['extra_config']:
      return 'xoom'
    if 'Neon' in builder_dict['extra_config']:
      return 'nexus_4'
    return {
      'x86': 'x86',
      'x86_64': 'x86_64',
      'Mips': 'mips',
      'Mips64': 'mips64',
      'MipsDSP2': 'mips_dsp2',
    }.get(builder_dict['target_arch'], 'arm_v7_thumb')
  elif builder_dict['os'] == 'Android':
    return {
      'NexusS': 'nexus_s',
      'Nexus4': 'nexus_4',
      'Nexus7': 'nexus_7',
      'Nexus10': 'nexus_10',
      'GalaxyNexus': 'galaxy_nexus',
      'Xoom': 'xoom',
      'IntelRhb': 'intel_rhb',
    }[builder_dict['model']]
  # pragma: no cover
  raise Exception('No device found for builder: %s' % str(builder_dict))


class AndroidFlavorUtils(default_flavor.DefaultFlavorUtils):
  def __init__(self, skia_api):
    super(AndroidFlavorUtils, self).__init__(skia_api)
    self.device = device_from_builder_dict(self._skia_api.c.builder_cfg)

  def compile(self, target):
    """Build the given target."""
    env = {}
    env['SKIA_ANDROID_VERBOSE_SETUP'] = 1
    env['ANDROID_SDK_ROOT'] = DEFAULT_ANDROID_SDK_ROOT
    env.update(self._skia_api.c.gyp_env.as_jsonish())
    env['BUILDTYPE'] = self._skia_api.c.configuration
    ccache = self._skia_api.ccache
    if ccache:
      env['ANDROID_MAKE_CCACHE'] = ccache

    cmd = [self._skia_api.m.path['checkout'].join('platform_tools', 'android',
                                                  'bin', 'android_ninja'),
           target, '-d', self.device]
    self._skia_api.m.step('build %s' % target, cmd, env=env,
                          cwd=self._skia_api.m.path['checkout'])
