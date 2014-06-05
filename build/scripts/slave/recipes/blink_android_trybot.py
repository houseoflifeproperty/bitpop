# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
  'step_history',
  'tryserver',
]


def GenSteps(api):
  api.chromium.set_config('blink', TARGET_PLATFORM='android')
  api.chromium.apply_config('trybot_flavor')
  api.chromium.apply_config('android')
  api.step.auto_resolve_conflicts = True

  # TODO(dpranke): crbug.com/348435. We need to figure out how to separate
  # out the retry and recovery logic from the rest of the recipe.

  yield api.gclient.checkout(revert=True, can_fail_build=False,
                             abort_on_failure=False)

  if any((step.retcode != 0) for step in api.step_history.values()):
    yield api.path.rmcontents('slave build directory', api.path['slave_build'])
    yield api.gclient.checkout()

  yield api.tryserver.maybe_apply_issue()
  yield api.chromium.runhooks()
  yield api.chromium.compile(abort_on_failure=False, can_fail_build=False)

  if api.step_history['compile'].retcode != 0:
    yield api.path.rmcontents('slave build directory', api.path['slave_build'])
    yield api.gclient.checkout(revert=False)
    yield api.tryserver.maybe_apply_issue()
    yield api.chromium.runhooks()
    yield api.chromium.compile()


def GenTests(api):
  yield (
    api.test('unittest_checkout_fails') +
    api.properties.tryserver(buildername='fake_trybot_buildername') +
    api.step_data('gclient revert', retcode=1)
  )

  yield (
    api.test('unittest_compile_fails') +
    api.properties.tryserver(buildername='fake_trybot_buildername') +
    api.step_data('compile', retcode=1)
  )

  yield (
      api.test('full_chromium_blink_blink_android_compile_rel') +
      api.properties.tryserver(buildername='blink_android_compile_rel') +
      api.platform.name('linux')
  )
