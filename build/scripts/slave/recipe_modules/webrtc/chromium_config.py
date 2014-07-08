# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import BadConf

from RECIPE_MODULES.chromium import CONFIG_CTX
from slave.recipe_config_types import Path


SUPPORTED_TARGET_ARCHS = ('intel', 'arm')


@CONFIG_CTX(includes=['chromium'])
def webrtc(c):
  c.compile_py.default_targets = ['All']

  c.memory_tests_runner = Path('[CHECKOUT]', 'tools', 'valgrind-webrtc',
                               'webrtc_tests', platform_ext={'win': '.bat',
                                                             'mac': '.sh',
                                                             'linux': '.sh'})


@CONFIG_CTX(includes=['chromium_clang'])
def webrtc_clang(c):
  c.compile_py.default_targets = ['All']


@CONFIG_CTX(includes=['chromium_tsan2'])
def webrtc_tsan2(c):
  c.compile_py.default_targets = ['All']


@CONFIG_CTX(includes=['android'])
def webrtc_android(c):
  pass


@CONFIG_CTX(includes=['android_clang'])
def webrtc_android_clang(c):
  pass


@CONFIG_CTX(includes=['android'])
def webrtc_android_apk(c):
  if c.TARGET_PLATFORM != 'android':
    raise BadConf('Only "android" platform is supported (got: "%s")' %
                  c.TARGET_PLATFORM)
  if c.TARGET_ARCH not in SUPPORTED_TARGET_ARCHS:
    raise BadConf('Only "%s" architectures are supported (got: "%s")' %
                  (','.join(SUPPORTED_TARGET_ARCHS), c.TARGET_ARCH))

  c.compile_py.default_targets = ['android_builder_webrtc']
  c.gyp_env.GYP_GENERATOR_FLAGS['default_target'] = 'android_builder_webrtc'
  c.gyp_env.GYP_DEFINES['include_tests'] = 1


@CONFIG_CTX(includes=['chromium', 'static_library'])
def webrtc_ios(c):
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('Only "mac" host platform is supported for iOS (got: "%s")' %
                  c.HOST_PLATFORM)
  if c.TARGET_PLATFORM != 'ios':
    raise BadConf('Only "ios" target platform is supported (got: "%s")' %
                  c.TARGET_PLATFORM)
  c.build_config_fs = c.BUILD_CONFIG + '-iphoneos'

  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['build_with_libjingle'] = 1
  gyp_defs['chromium_ios_signing'] = 0
  gyp_defs['key_id'] = ''
  gyp_defs['target_arch'] = 'armv7'
  gyp_defs['OS'] = c.TARGET_PLATFORM

  c.compile_py.default_targets = ['All']
