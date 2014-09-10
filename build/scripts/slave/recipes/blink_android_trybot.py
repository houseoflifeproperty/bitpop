# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
  'tryserver',
]

def GenSteps(api):
  api.chromium.set_config('blink', TARGET_PLATFORM='android', TARGET_ARCH='arm')
  api.chromium.apply_config('trybot_flavor')
  api.chromium.apply_config('android')
  api.gclient.apply_config('android')
  api.step.auto_resolve_conflicts = True

  # TODO(dpranke): crbug.com/348435. We need to figure out how to separate
  # out the retry and recovery logic from the rest of the recipe.

  step_result = api.bot_update.ensure_checkout()
  # The first time we run bot update, remember if bot_update mode is on or off.
  bot_update_mode = step_result.json.output['did_run']
  if not bot_update_mode:
    try:
      api.gclient.checkout(revert=True)
    except api.step.StepFailure:
      api.path.rmcontents('slave build directory',
                                api.path['slave_build'])
      api.gclient.checkout(revert=False)
    api.tryserver.maybe_apply_issue()

  api.chromium.runhooks()
  step_result = None
  try:
    step_result = api.chromium.compile()
  except api.step.StepFailure:
    api.path.rmcontents('slave build directory', api.path['slave_build'])
    if bot_update_mode:
      api.bot_update.ensure_checkout(suffix='clean')
    else:
      api.gclient.checkout(revert=False)
      api.tryserver.maybe_apply_issue()
    api.chromium.runhooks()
    api.chromium.compile()


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

  yield (
      api.test('bot_update_on') +
      api.properties.tryserver(buildername='fake_trybot_buildername',
                               mastername='bot_update.always_on') +
      api.step_data('compile', retcode=1)
  )
