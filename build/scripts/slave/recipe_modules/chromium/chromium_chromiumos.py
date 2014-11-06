# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-chromiumos-archive',
  },
  'builders': {
    'Linux ChromiumOS Full': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'app_list_unittests',
        'aura_builder',
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
        'chromeos_unittests',
        'components_unittests',
        'compositor_unittests',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        'dbus_unittests',
        'device_unittests',
        'gcm_unit_tests',
        'google_apis_unittests',
        'gpu_unittests',
        'interactive_ui_tests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'message_center_unittests',
        'nacl_loader_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'ui_unittests',
        'unit_tests',
        'url_unittests',
        'views_unittests',
      ],
      'tests': [
        steps.ArchiveBuildStep(
            'chromium-browser-snapshots',
            gs_acl='public-read',
        ),
        steps.Deps2GitTest(),
        steps.CheckpermsTest(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux ChromiumOS Builder': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Tests (1)': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux ChromiumOS Tests (2)': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Linux ChromiumOS (Clang dbg)': {
      'recipe_config': 'chromium_chromeos_clang',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'app_list_unittests',
        'aura_builder',
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
        'chromeos_unittests',
        'components_unittests',
        'compositor_unittests',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        'dbus_unittests',
        'device_unittests',
        'gcm_unit_tests',
        'google_apis_unittests',
        'gpu_unittests',
        'interactive_ui_tests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'message_center_unittests',
        'nacl_loader_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'ui_unittests',
        'unit_tests',
        'url_unittests',
        'views_unittests',
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux ChromiumOS Ozone Builder': {
      'recipe_config': 'chromium_chromeos_ozone',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux ChromiumOS Ozone Tests (1)': {
      'recipe_config': 'chromium_chromeos_ozone',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Ozone Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux ChromiumOS Ozone Tests (2)': {
      'recipe_config': 'chromium_chromeos_ozone',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Ozone Builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux ChromiumOS Builder (dbg)': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Tests (dbg)(1)': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux ChromiumOS Tests (dbg)(2)': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux ChromiumOS Tests (dbg)(3)': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    # Simple Chrome test builder for coverage
    'Coverage ChromiumOS Simple Chrome x86-generic': {
      'recipe_config': 'chromium_chromeos',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_CROS_BOARD': 'x86-generic',
      },
      'bot_type': 'builder',
      'disable_tests': True,
      'compile_targets': [
        'chrome',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
