# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-mac-archive',
  },
  'builders': {
    'Mac Builder': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_tests',
      ],
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac10.6 Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.NaclIntegrationTest(),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac10.6 Tests (2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac10.7 Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.NaclIntegrationTest(),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac10.7 Tests (2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac Builder (dbg)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_tests',
      ],
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac 10.6 Tests (dbg)(1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.NaclIntegrationTest(),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac 10.6 Tests (dbg)(2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac 10.7 Tests (dbg)(1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.NaclIntegrationTest(),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      }
    },
    'Mac 10.7 Tests (dbg)(2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      }
    },
    'iOS Device': {
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
    'iOS Simulator (dbg)': {
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
    'iOS Device (ninja)': {
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
  },
}
