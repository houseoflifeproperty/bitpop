# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'builders': {
    'Google Chrome ChromeOS': {
      'recipe_config': 'chromeos_official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'chrome',
        'chrome_sandbox',
        'linux_symbols',
        'symupload'
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome Linux': {
      'recipe_config': 'official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome Linux x64': {
      'recipe_config': 'official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome Mac': {
      'recipe_config': 'official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'testing': {
        'platform': 'mac',
      },
    },
    'Google Chrome Win': {
      'recipe_config': 'official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'testing': {
        'platform': 'win',
      },
    },
  },
}
