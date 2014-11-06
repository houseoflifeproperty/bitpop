# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-memory-archive',
  },
  'builders': {
    'Linux ASan LSan Builder': {
      'recipe_config': 'chromium_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
    },
  },
}

for name in ('Linux ASan LSan Tests (1)',
             'Linux ASan LSan Tests (2)',
             'Linux ASan LSan Tests (3)',
             'Linux ASan Tests (sandboxed)'):
  SPEC['builders'][name] = {
    'recipe_config': 'chromium_asan',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'tester',
    'test_generators': [
      steps.generate_gtest,
    ],
    'parent_buildername': 'Linux ASan LSan Builder',
    'testing': {'platform': 'linux'},
  }

# LSan is not sandbox-compatible, which is why testers 1-3 have the sandbox
# disabled. This tester runs the same tests again with the sandbox on and LSan
# disabled. This only affects browser tests. See http://crbug.com/336218
SPEC['builders']['Linux ASan Tests (sandboxed)']['chromium_apply_config'] = (
    ['no_lsan'])
