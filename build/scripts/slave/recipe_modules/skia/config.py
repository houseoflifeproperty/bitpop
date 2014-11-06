# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Set, Single, Static
from slave.recipe_config_types import Path

from common.skia import builder_name_schema
from . import slaves_cfg


CONFIG_DEBUG = 'Debug'
CONFIG_RELEASE = 'Release'
VALID_CONFIGS = (CONFIG_DEBUG, CONFIG_RELEASE)


def BaseConfig(BUILDER_NAME, MASTER_NAME, SLAVE_NAME, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % tup)
  return ConfigGroup(
    BUILDER_NAME = Static(str(BUILDER_NAME)),
    MASTER_NAME = Static(str(MASTER_NAME)),
    SLAVE_NAME = Static(str(SLAVE_NAME)),
    build_targets = Single(list),
    builder_cfg = Single(dict),
    configuration = Single(str),
    do_test_steps = Single(bool),
    do_perf_steps = Single(bool),
    gyp_env = ConfigGroup(
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
    ),
    is_trybot = Single(bool),
    role = Single(str),
    slave_cfg = Single(dict)
  )


VAR_TEST_MAP = {
  'BUILDER_NAME': (u'Build-Mac10.7-Clang-Arm7-Debug-iOS',
                   u'Build-Ubuntu13.10-GCC4.8-NaCl-Debug',
                   u'Build-Ubuntu13.10-GCC4.8-x86_64-Debug',
                   u'Build-Win-VS2013-x86-Debug-Exceptions',
                   u'Housekeeper-PerCommit',
                   u'Test-Mac10.8-MacMini4.1-GeForce320M-x86_64-Release',
                   u'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Debug-ZeroGPUCache',
                   u'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Release-Valgrind',
                   u'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Release-Shared',
                   u'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Release-TSAN',
                   u'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes',
                   u'Test-Win7-ShuttleA-HD2000-x86-Debug-GDI',
                   u'Test-Win7-ShuttleA-HD2000-x86-Release-ANGLE',
                   u'Test-Win8-ShuttleA-GTX660-x86-Release'),
  'MASTER_NAME': (u'client.skia',),
  'SLAVE_NAME': (u'skiabot-linux-tester-004',),
}


def gyp_defs_from_builder_dict(builder_dict):
  gyp_defs = {}

  # skia_arch_width.
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_BUILD:
    arch = builder_dict['target_arch']
  elif builder_dict['role'] == builder_name_schema.BUILDER_ROLE_HOUSEKEEPER:
    arch = None
  else:
    arch = builder_dict['arch']
  skia_arch_width = {
    'x86': '32',
    'x86_64': '64',
    'Arm7': '32',
    'Arm64': '64',
    'Mips': '32',
    'Mips64': '64',
    'MipsDSP2': '32',
    'NaCl': None,
  }.get(arch)
  if skia_arch_width:
    gyp_defs['skia_arch_width'] = skia_arch_width

  # skia_gpu.
  if (builder_dict.get('gpu') == 'NoGPU' or
      builder_dict.get('model') == 'IntelRHB'):
    gyp_defs['skia_gpu'] = '0'

  # skia_warnings_as_errors.
  if builder_dict['role'] == builder_name_schema.BUILDER_ROLE_BUILD:
    gyp_defs['skia_warnings_as_errors'] = '1'
  else:
    gyp_defs['skia_warnings_as_errors'] = '0'

  # Win debugger.
  if 'Win' in builder_dict.get('os', ''):
    gyp_defs['skia_win_debuggers_path'] = 'c:/DbgHelp'

  # Qt SDK (Win).
  if 'Win' in builder_dict.get('os', ''):
    if builder_dict.get('os') == 'Win8':
      gyp_defs['qt_sdk'] = 'C:/Qt/Qt5.1.0/5.1.0/msvc2012_64/'
    else:
      gyp_defs['qt_sdk'] = 'C:/Qt/4.8.5/'

  # ANGLE.
  if builder_dict.get('extra_config') == 'ANGLE':
    gyp_defs['skia_angle'] = '1'

  # GDI.
  if builder_dict.get('extra_config') == 'GDI':
    gyp_defs['skia_gdi'] = '1'

  # Build with Exceptions on Windows.
  if ('Win' in builder_dict.get('os', '') and
      builder_dict.get('extra_config') == 'Exceptions'):
    gyp_defs['skia_win_exceptions'] = '1'

  # iOS.
  if (builder_dict.get('os') == 'iOS' or
      builder_dict.get('extra_config') == 'iOS'):
    gyp_defs['skia_os'] = 'ios'

  # Shared library build.
  if builder_dict.get('extra_config') == 'Shared':
    gyp_defs['skia_shared_lib'] = '1'

  # PDF viewer in GM.
  if (builder_dict.get('os') == 'Mac10.8' and
      builder_dict.get('arch') == 'x86_64' and
      builder_dict.get('configuration') == 'Release'):
    gyp_defs['skia_run_pdfviewer_in_gm'] = '1'

  # Clang.
  if builder_dict.get('compiler') == 'Clang':
    gyp_defs['skia_clang_build'] = '1'

  # Valgrind.
  if builder_dict.get('extra_config') == 'Valgrind':
    gyp_defs['skia_release_optimization_level'] = '1'

  return gyp_defs


def build_targets_from_builder_dict(builder_dict):
  """Return a list of targets to build, depending on the builder type."""
  if builder_dict.get('target_arch') == 'NaCl':
    return ['skia_lib', 'debugger']
  elif builder_dict.get('extra_config') == 'ZeroGPUCache':
    return ['gm']
  elif (builder_dict['role'] == builder_name_schema.BUILDER_ROLE_TEST and
        builder_dict.get('extra_config') == 'TSAN'):
    return ['dm']
  elif builder_dict['role'] == builder_name_schema.BUILDER_ROLE_HOUSEKEEPER:
    return ['tools', 'gm', 'dm']
  else:
    return ['most']


config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, '%(BUILDER_NAME)s')


@config_ctx(is_root=True)
def skia(c):
  """Base config for Skia."""
  c.builder_cfg = builder_name_schema.DictForBuilderName(c.BUILDER_NAME)
  c.build_targets = build_targets_from_builder_dict(c.builder_cfg)
  c.configuration = c.builder_cfg.get('configuration', CONFIG_DEBUG)
  c.role = c.builder_cfg['role']
  c.do_test_steps = c.role == builder_name_schema.BUILDER_ROLE_TEST
  c.do_perf_steps = (c.role == builder_name_schema.BUILDER_ROLE_PERF or
                     (c.role == builder_name_schema.BUILDER_ROLE_TEST and
                      c.configuration == CONFIG_DEBUG) or
                     'Valgrind' in c.BUILDER_NAME)
  c.gyp_env.GYP_DEFINES.update(gyp_defs_from_builder_dict(c.builder_cfg))
  c.slave_cfg = slaves_cfg.get(c.MASTER_NAME)[c.SLAVE_NAME]
  c.is_trybot = builder_name_schema.IsTrybot(c.BUILDER_NAME)

