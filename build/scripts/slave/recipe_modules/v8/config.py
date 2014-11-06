# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from os import path

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import List, Set, Single, Static


def BaseConfig(**_kwargs):
  shard_count = _kwargs.get('SHARD_COUNT', 1)
  shard_run = _kwargs.get('SHARD_RUN', 1)
  assert shard_count >= 1
  assert shard_run >= 1
  assert shard_run <= shard_count

  return ConfigGroup(
    compile_py = ConfigGroup(
      compile_extra_args = List(basestring),
    ),
    gyp_env = ConfigGroup(
      CC = Single(basestring, required=False),
      CXX = Single(basestring, required=False),
      CXX_host = Single(basestring, required=False),
      LINK = Single(basestring, required=False),
    ),
    nacl = ConfigGroup(
      update_nacl_sdk = Single(basestring, required=False),
      NACL_SDK_ROOT = Single(basestring, required=False),
    ),
    # Test configuration that is the equal for all tests of a builder. It
    # might be refined later in the test runner for distinct tests.
    testing = ConfigGroup(
      add_flaky_step = Single(bool, required=False),

      # Show test results on waterfall UI. Switch for backwards-compatibility
      # with the stand-alone test driver on older branches.
      # TODO(machenbach): Remove this switch when the feature is available on
      # all branches.
      show_test_results = Single(bool, empty_val=True, required=False),
      test_args = Set(basestring),

      SHARD_COUNT = Static(shard_count),
      SHARD_RUN = Static(shard_run),
    ),
  )


config_ctx = config_item_context(BaseConfig, {}, 'v8')


@config_ctx()
def v8(c):
  pass


@config_ctx()
def android_arm(c):
  # Make is executed in the out dir. Android points to the toplevel Makefile in
  # the v8 dir.
  c.compile_py.compile_extra_args.extend(['-C', '..' , 'android_arm.release'])


@config_ctx()
def arm_hard_float(c):
  c.gyp_env.CXX = '/usr/bin/arm-linux-gnueabihf-g++'
  c.gyp_env.LINK = '/usr/bin/arm-linux-gnueabihf-g++'


@config_ctx()
def deadcode(c):
  c.testing.test_args.add('--shell_flags="--dead-code-elimination"')


@config_ctx()
def deopt_fuzz_normal(c):
  c.testing.test_args.add('--coverage=0.4')
  c.testing.test_args.add('--distribution-mode=smooth')


@config_ctx()
def deopt_fuzz_random(c):
  c.testing.test_args.add('--coverage=0.4')
  c.testing.test_args.add('--coverage-lift=50')
  c.testing.test_args.add('--distribution-mode=random')


@config_ctx()
def gc_stress(c):
  c.testing.test_args.add('--gc-stress')


@config_ctx()
def isolates(c):
  c.testing.test_args.add('--isolates=on')


@config_ctx()
def nacl(c):
  c.testing.test_args.add('--command_prefix=%s'
                          % path.join('tools', 'nacl-run.py'))
  # This switches off buildbot flavor for NaCl, i.e. uses the directory layout
  # out/nacl_ia32.release instead of out/Release.
  c.testing.test_args.add('--buildbot=False')
  c.testing.test_args.add('--no-presubmit')


@config_ctx(includes=['nacl'])
def nacl_stable(c):
  c.nacl.update_nacl_sdk = 'stable'


@config_ctx(includes=['nacl'])
def nacl_canary(c):
  c.nacl.update_nacl_sdk = 'canary'


@config_ctx(includes=['nacl'])
def nacl_ia32(c):
  # Make is executed in the out dir. NaCl points to the toplevel Makefile in
  # the v8 dir.
  c.compile_py.compile_extra_args.extend(['-C', '..' , 'nacl_ia32.release'])


@config_ctx(includes=['nacl'])
def nacl_x64(c):
  # Make is executed in the out dir. NaCl points to the toplevel Makefile in
  # the v8 dir.
  c.compile_py.compile_extra_args.extend(['-C', '..' , 'nacl_x64.release'])


@config_ctx()
def no_i18n(c):
  c.testing.test_args.add('--noi18n')


@config_ctx()
def no_snapshot(c):
  c.testing.test_args.add('--no-snap')


@config_ctx()
def nosse3(c):
  c.testing.test_args.add('--shell_flags="--noenable-sse3"')


@config_ctx()
def nosse4(c):
  c.testing.test_args.add('--shell_flags="--noenable-sse4-1"')


@config_ctx()
def no_test_results(c):
  c.testing.show_test_results = False


@config_ctx()
def no_variants(c):
  c.testing.test_args.add('--no-variants')


@config_ctx()
def novfp3(c):
  c.testing.test_args.add('--shell_flags="--noenable-vfp3"')


@config_ctx()
def predictable(c):
  c.testing.test_args.add('--predictable')


@config_ctx()
def trybot_flavor(c):
  c.testing.add_flaky_step = False
  c.testing.test_args.add('--flaky-tests=skip')
