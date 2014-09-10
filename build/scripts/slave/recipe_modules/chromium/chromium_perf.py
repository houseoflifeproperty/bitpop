# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

def _Spec(platform, parent_builder, browser, perf_id, index, num_shards):
  return {
    'bot_type': 'tester',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'parent_buildername': parent_builder,
    'perf_tester_shards': num_shards,
    'recipe_config': 'chromium',
    'testing': {
      'platform': platform,
    },
    'tests': [
      steps.DynamicPerfTests(browser, perf_id, index, num_shards),
    ],
  }

SPEC = {
  'settings': {
    'build_gs_bucket': 'chrome-perf',
  },
  'builders': {
    'Linux Builder': {
      'no_test_spec': True,
      'recipe_config': 'official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Oilpan Builder': {
      'no_test_spec': True,
      'recipe_config': 'chromium_oilpan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Perf (1)': _Spec('linux', 'Linux Builder', 'release',
                            'linux-release', 0, 5),
    'Linux Perf (2)': _Spec('linux', 'Linux Builder', 'release',
                            'linux-release', 1, 5),
    'Linux Perf (3)': _Spec('linux', 'Linux Builder', 'release',
                            'linux-release', 2, 5),
    'Linux Perf (4)': _Spec('linux', 'Linux Builder', 'release',
                            'linux-release', 3, 5),
    'Linux Perf (5)': _Spec('linux', 'Linux Builder', 'release', 'linux', 4, 5),
    'Linux Oilpan Perf (1)': _Spec('linux', 'Linux Oilpan Builder', 'release',
                                   'linux-oilpan-release', 0, 4),
    'Linux Oilpan Perf (2)': _Spec('linux', 'Linux Oilpan Builder', 'release',
                                   'linux-oilpan-release', 1, 4),
    'Linux Oilpan Perf (3)': _Spec('linux', 'Linux Oilpan Builder', 'release',
                                   'linux-oilpan-release', 2, 4),
    'Linux Oilpan Perf (4)': _Spec('linux', 'Linux Oilpan Builder', 'release',
                                   'linux-oilpan-release', 3, 4),
  },
}