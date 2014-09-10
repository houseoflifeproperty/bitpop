# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-v8',
  },
  'builders': {
    'Linux Debug Builder': {
      'recipe_config': 'chromium_v8',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'set_component_rev': {'name': 'src/v8', 'rev_str': 'bleeding_edge:%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    # Bot names should be in sync with chromium.linux's names to retrieve the
    # same test configuration files.
    'Linux Tests (dbg)(1)': {
      'recipe_config': 'chromium_v8',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'set_component_rev': {'name': 'src/v8', 'rev_str': 'bleeding_edge:%s'},
      'tests': [
        steps.DynamicGTestTests('Linux Tests (dbg)(1)'),
      ],
      'parent_buildername': 'Linux Debug Builder',
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
  },
}
