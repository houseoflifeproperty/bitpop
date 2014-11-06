# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-memory-fyi-archive',
  },
  'builders': {
    'Chromium Linux MSan Builder': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        'msan': 1,
        'msan_track_origins': 0,
        'use_instrumented_libraries': 1,
        'instrumented_libraries_jobs': 10,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux MSan Tests': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        # Required on testers to pass the right runtime flags.
        # TODO(earthdok): make this part of a chromium_msan recipe config.
        'msan': 1,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux MSan Browser (1)': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        # Required on testers to pass the right runtime flags.
        # TODO(earthdok): make this part of a chromium_msan recipe config.
        'msan': 1,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux MSan Browser (2)': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        # Required on testers to pass the right runtime flags.
        # TODO(earthdok): make this part of a chromium_msan recipe config.
        'msan': 1,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux MSan Browser (3)': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        # Required on testers to pass the right runtime flags.
        # TODO(earthdok): make this part of a chromium_msan recipe config.
        'msan': 1,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
