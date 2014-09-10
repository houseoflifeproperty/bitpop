# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


DEPS = [
  'path',
  'properties',
  'raw_io',
  'skia',
]


def GenSteps(api):
  api.skia.gen_steps()

def GenTests(api):
  builders = [
    'Build-Ubuntu13.10-GCC4.8-x86_64-Debug',
    'Perf-ChromeOS-Daisy-MaliT604-Arm7-Release',
    'Test-Android-Nexus10-MaliT604-Arm7-Release',
    'Test-Android-Xoom-Tegra2-Arm7-Release',
    'Test-Mac10.8-MacMini4.1-GeForce320M-x86_64-Debug',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Release-Valgrind',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Debug-ZeroGPUCache',
    'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes',
    'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Release-TSAN',
    'Test-Win7-ShuttleA-HD2000-x86-Release',
    'Test-Win7-ShuttleA-HD2000-x86-Release-ANGLE',
  ]
  for builder in builders:
    test = (
      api.test(builder) +
      api.properties(buildername=builder) +
      api.path.exists(
          api.path['slave_build'].join(
              'skia', 'expectations', 'gm',
              'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes',
              'expected-results.json'),
          api.path['slave_build'].join('skia', 'expectations', 'gm',
                                       'ignored-tests.txt'),
      )
    )
    if 'Android' in builder or 'NaCl' in builder:
      test += api.step_data('has ccache?', retcode=1)
    yield test

  builder = 'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes'
  yield (
    api.test('failed_gm') +
    api.properties(buildername=builder) +
    api.step_data('gm', retcode=1)
  )

  yield (
    api.test('has_ccache_android') +
    api.properties(buildername='Build-Ubuntu13.10-GCC4.8-Arm7-Debug-Android') +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
  )

  yield (
    api.test('has_ccache_nacl') +
    api.properties(buildername='Build-Ubuntu13.10-GCC4.8-NaCl-Debug') +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
  )
