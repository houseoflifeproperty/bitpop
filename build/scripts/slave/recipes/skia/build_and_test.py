# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


DEPS = [
  'properties',
  'skia',
]


def GenSteps(api):
  api.skia.setup()
  yield api.skia.checkout_steps()
  yield api.skia.compile_steps()
  yield api.skia.test_steps()


def GenTests(api):
  yield (
    api.test('linux_debug_build') +
    api.properties(build_config='Debug',
                   buildername='Test-Ubuntu12-ShuttleA-NoGPU-x86_64-Debug')
  )
  yield (
    api.test('linux_debug_build_no_catchsegv') +
    api.properties(
        build_config='Debug',
        buildername='Test-Ubuntu13-ShuttleA-HD2000-x86_64-Debug-TSAN')
  )
  yield (
    api.test('linux_trybot') +
    api.properties(build_config='Debug',
                   buildername='Test-Ubuntu12-ShuttleA-NoGPU-x86_64-Debug',
                   rietveld='https://codereview.chromium.org',
                   issue='12853011',
                   patchset='1')
  )
