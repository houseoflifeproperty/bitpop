# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the V8 builder configurations so they can be reused
# from multiple recipes.

BUILDERS = {
####### Waterfall: client.v8
  'client.v8': {
    'builders': {
####### Category: Linux
      'V8 Linux - builder': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug builder': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap builder': {
        'chromium_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap debug builder': {
        'chromium_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        # TODO(machenbach): This is an experimental performance test step.
        # Remove as soon as development on this step has completed.
        'perf': ['experimental'],
        'tests': [
          'presubmit',
          'v8initializers',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'benchmarks',
          'test262',
          'mozilla',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': [
          'v8testing',
          'benchmarks',
          'test262',
          'mozilla',
          'simpleleak',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - shared': {
        'chromium_apply_config': ['shared_library', 'verify_heap'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap': {
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap - debug': {
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap debug builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - isolates': {
        'v8_apply_config': ['isolates'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse2': {
        'v8_apply_config': ['nosse2'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla', 'gcmole'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse3': {
        'v8_apply_config': ['nosse3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse4': {
        'v8_apply_config': ['nosse4'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - deadcode': {
        'v8_apply_config': ['deadcode'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - isolates': {
        'v8_apply_config': ['isolates'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse2': {
        'v8_apply_config': ['nosse2'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse3': {
        'v8_apply_config': ['nosse3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse4': {
        'v8_apply_config': ['nosse4'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - interpreted regexp': {
        'chromium_apply_config': ['interpreted_regexp'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - noi18n - debug': {
        'v8_apply_config': ['no_i18n'],
        'chromium_apply_config': ['no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'mozilla', 'test262'],
        'testing': {'platform': 'linux'},
      },
####### Category: Linux64
      'V8 Linux64 - builder': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug builder': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - builder',
        'build_gs_archive': 'linux64_rel_archive',
        'tests': [
          'v8initializers',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'test262',
          'mozilla',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
####### Category: Windows
      'V8 Win32 - 1': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - builder',
        'build_gs_archive': 'win32_rel_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - 2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - builder',
        'build_gs_archive': 'win32_rel_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - nosnap - shared': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['shared_library', 'no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 1': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 3': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 3,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win64': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'win'},
      },
####### Category: Mac
      'V8 Mac': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'mac'},
      },
####### Category: Arm
# TODO(machenbach): Enable i18n as soon as icu dynamically ensures the -m32
# compilation option.
      'V8 Arm': {
        'v8_apply_config': ['no_i18n'],
        'chromium_apply_config': ['no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'optimize_for_size'],
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug': {
        'v8_apply_config': ['no_i18n'],
        'chromium_apply_config': ['no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'optimize_for_size'],
        'testing': {'platform': 'linux'},
      },
####### Category: Simulators
      'V8 Linux - arm - sim': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - novfp3': {
        # TODO(machenbach): Can these configs be reduced to one?
        'chromium_apply_config': ['novfp3'],
        'v8_apply_config': ['novfp3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - debug - novfp3': {
        'chromium_apply_config': ['novfp3'],
        'v8_apply_config': ['novfp3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - nosnap - debug - 1': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - nosnap - debug - 2': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'test262', 'mozilla'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - gc stress': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - mips - sim': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'mipsel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'test262'],
        'testing': {'platform': 'linux'},
      },
####### Category: Misc
      'V8 Fuzzer': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': ['fuzz'],
        'testing': {'platform': 'linux'},
      },
      'V8 GC Stress - 1': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 GC Stress - 2': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 GC Stress - 3': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 3,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac GC Stress - 1': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 1,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac GC Stress - 2': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 2,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac GC Stress - 3': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 3,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'mac'},
      },
      'V8 Arm GC Stress': {
        'v8_apply_config': ['gc_stress', 'no_i18n'],
        'chromium_apply_config': ['no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN': {
        'gclient_apply_config': ['clang'],
        'chromium_apply_config': ['clang', 'asan', 'no_lsan'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
####### Category: FYI
      'V8 Linux - vtunejit': {
        'chromium_apply_config': ['vtunejit'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - x87 - nosnap - debug': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot', 'x87'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - full debug builder': {
        'chromium_apply_config': ['no_optimized_debug'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Mac - full debug': {
        'chromium_apply_config': ['no_optimized_debug'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'mac'},
      },
    },
  },
####### Waterfall: tryserver.v8
  'tryserver.v8': {
    'builders': {
      'v8_linux_rel': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_dbg': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nosnap_rel': {
        'chromium_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nosnap_dbg': {
        'chromium_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_rel': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_win_rel': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'win'},
      },
      'v8_mac_rel': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'mac'},
      },
      'v8_linux_arm_dbg': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_rel': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
    },
  },
}

####### Waterfall: client.v8.branches
BRANCH_BUILDERS = {}

def AddBranchBuilder(branch_config, build_config, arch, bits, presubmit=False):
  tests = ['v8testing', 'webkit', 'test262', 'mozilla']
  if presubmit:
    tests = ['presubmit'] + tests
  return {
    'gclient_apply_config': [branch_config],
    'chromium_apply_config': ['no_optimized_debug'],
    # TODO(machenbach): Switch on test results presentation for branch builders
    # as soon as stable branch passes v8 revision 21358, where the feature was
    # introduced.
    'v8_apply_config': ['no_test_results'],
    'v8_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_ARCH': arch,
      'TARGET_BITS': bits,
    },
    'bot_type': 'builder_tester',
    'tests': tests,
    'testing': {'platform': 'linux'},
  }

for build_config, name_suffix in (('Release', ''), ('Debug', ' - debug')):
  for branch_name, branch_config in (('stable branch', 'stable_branch'),
                                     ('beta branch', 'beta_branch'),
                                     ('trunk', 'trunk')):
    name = 'V8 Linux - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        branch_config, build_config, 'intel', 32, presubmit=True)
    name = 'V8 Linux64 - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        branch_config, build_config, 'intel', 64)
    name = 'V8 arm - sim - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        branch_config, build_config, 'arm', 32)

BUILDERS['client.v8.branches'] = {'builders': BRANCH_BUILDERS}
