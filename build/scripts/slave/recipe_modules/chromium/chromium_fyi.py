# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
    'Chromium iOS Device': {
      'recipe_config': 'chromium_ios_device',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'ios',
        'TARGET_BITS': 32,
      },
      'gclient_config_kwargs': {
        'GIT_MODE': True,
      },
      'testing': {
        'platform': 'mac',
      }
    },
    'Chromium iOS Simulator (dbg)': {
      'recipe_config': 'chromium_ios_simulator',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'ios',
        'TARGET_BITS': 32,
      },
      'gclient_config_kwargs': {
        'GIT_MODE': True,
      },
      'tests': steps.IOS_TESTS,
      'testing': {
        'platform': 'mac',
      }
    },
    'Chromium iOS Device (ninja)': {
      'recipe_config': 'chromium_ios_ninja',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'ios',
        'TARGET_BITS': 64,
      },
      'gclient_config_kwargs': {
        'GIT_MODE': True,
      },
      'testing': {
        'platform': 'mac',
      }
    },
    'Linux ARM Cross-Compile': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'GYP_DEFINES': {
        'target_arch': 'arm',
        'arm_float_abi': 'hard',
        'test_isolation_mode': 'archive',
      },
      'chromium_config': 'chromium',
      'runhooks_env': {
        'GYP_CROSSCOMPILE': '1',
      },
      'tests': [
        steps.DynamicGTestTests('Linux ARM Cross-Compile'),
      ],
      'testing': {
        'platform': 'linux',
      },
      'do_not_run_tests': True,
      'use_isolate': True,
    },
    'Linux Trusty': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (32)': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty (32)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (dbg)': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty (dbg)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (dbg)(32)': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty (dbg)(32)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux MSan Builder': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        'msan': 1,
        'msan_track_origins': 2,
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
      'tests': [
        steps.DynamicGTestTests('Linux MSan Tests'),
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
      'tests': [
        steps.DynamicGTestTests('Linux MSan Browser (1)'),
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
      'tests': [
        steps.DynamicGTestTests('Linux MSan Browser (2)'),
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
      'tests': [
        steps.DynamicGTestTests('Linux MSan Browser (3)'),
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Print Preview Linux': {
      'recipe_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'linux',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'Print Preview Mac': {
      'recipe_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'mac',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'mac',
      },
    },
    'Print Preview Win': {
      'recipe_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'win',
      },
    },
  },
}
