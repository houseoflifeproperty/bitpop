# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU builders on the
# following waterfalls:
#   chromium.gpu
#   chromium.gpu.fyi
#   chromium.webkit

DEPS = [
  'buildbot',
  'gpu',
  'platform',
  'properties',
]

def GenSteps(api):
  api.gpu.setup()
  api.buildbot.prep()
  api.gpu.checkout_steps()
  api.gpu.compile_steps()

def GenTests(api):
  # The majority of the tests are in the build_and_test recipe.

  # Keep the additional properties in sync with the download_and_test
  # recipe in order to catch regressions.
  for plat in ['win', 'mac', 'linux']:
    for flavor in ['Debug', 'Release']:
      flavor_lower = flavor.lower()
      yield (
        api.test('%s_%s' % (plat, flavor_lower)) +
        api.properties.scheduled(
          build_config=flavor,
          mastername='chromium.gpu.testing',
          buildername='%s %s builder' % (plat, flavor_lower),
          buildnumber=571) +
        api.platform.name(plat)
      )

  # Test one configuration where it's expected that top-of-tree ANGLE
  # will be used.
  yield (
    api.test('win_release_tot_angle') +
    api.properties.scheduled(
      build_config='Release',
      mastername='chromium.gpu.fyi',
      buildername='win release tot angle builder',
      buildnumber=572) +
    api.platform.name('win')
  )

  # Test one configuration where 'gclient revert' fails.
  yield (
    api.test('win_release_gclient_revert_failure') +
    api.properties.scheduled(
      build_config='Release',
      mastername='chromium.gpu.testing',
      buildername='win release builder',
      buildnumber=571) +
    api.step_data('gclient revert', retcode=1) +
    api.platform.name('win')
  )

  # Test one tryserver configuration when the initial compile fails.
  yield (
    api.test('clobber_after_tryserver_failed_compile') +
    api.properties.tryserver(build_config='Release') +
    api.platform.name('linux') +
    api.step_data('compile', retcode=1)
  )

  yield (
    api.test('compile_fail_is_critical_on_main') +
    api.properties.scheduled(
      build_config='Release',
      mastername='chromium.gpu.testing',
      buildername='linux release builder',
      buildnumber=571) +
    api.platform.name('linux') +
    api.step_data('compile', retcode=1)
  )
