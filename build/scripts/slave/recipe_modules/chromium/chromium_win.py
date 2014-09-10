# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-win-archive',
  },
  'builders': {
    'Win Builder': {
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
        'platform': 'win',
      },
    },
    'XP Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('XP Tests (1)'),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'XP Tests (2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('XP Tests (2)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'XP Tests (3)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('XP Tests (3)'),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Vista Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Vista Tests (1)'),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Vista Tests (2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Vista Tests (2)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Vista Tests (3)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Vista Tests (3)'),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (1)'),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (2)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (3)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (3)'),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Sync': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.GTestTest('sync_integration_tests', args=[
            '--ui-test-action-max-timeout=120000'
        ]),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },

    'Win x64 Builder': {
      'recipe_config': 'chromium',
      'chromium_apply_config': ['shared_library'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'all',
      ],
      'testing': {
        'platform': 'win',
      },
    },
    'Win 7 Tests x64 (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win 7 Tests x64 (1)'),
      ],
      'parent_buildername': 'Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win 7 Tests x64 (2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win 7 Tests x64 (2)'),
      ],
      'parent_buildername': 'Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win 7 Tests x64 (3)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win 7 Tests x64 (3)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
      ],
      'parent_buildername': 'Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Sync x64': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.GTestTest('sync_integration_tests', args=[
            '--ui-test-action-max-timeout=120000'
        ]),
      ],
      'parent_buildername': 'Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
    },

    'NaCl Tests (x86-32)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.NaclIntegrationTest(),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },
    'NaCl Tests (x86-64)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.NaclIntegrationTest(),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
    },

    'Win x64 Builder (dbg)': {
      'recipe_config': 'chromium',
      'chromium_apply_config': ['shared_library'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'all',
      ],
      'testing': {
        'platform': 'win',
      },
    },

    'Win Builder (dbg)': {
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
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (dbg)(1)'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(2)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (dbg)(2)'),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(3)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (dbg)(3)'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(4)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (dbg)(4)'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(5)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (dbg)(5)'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(6)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win7 Tests (dbg)(6)'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Interactive Tests (dbg)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Interactive Tests (dbg)'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
    'Win8 Aura': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'tests': [
        steps.DynamicGTestTests('Win8 Aura'),
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
    },
  },
}
