# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
]


def _CheckoutSteps(api):
  # Checkout pdfium and its dependencies (specified in DEPS) using gclient
  api.gclient.set_config('pdfium')
  api.gclient.checkout()


def _BuildSteps(api):
  # Generate build files for Ninja
  gyp_path = api.path['checkout'].join('build', 'gyp_pdfium')
  api.step('gyp_pdfium', [gyp_path], env = {'GYP_GENERATORS': 'ninja'})

  # Build sample file using Ninja
  debug_path = api.path['checkout'].join('out', 'Debug')
  api.step('compile with ninja',
      ['ninja', '-C', debug_path, 'pdfium_test'])


def GenSteps(api):
  _CheckoutSteps(api)
  _BuildSteps(api)


def GenTests(api):
  yield api.test('win') + api.platform('win', 64)
  yield api.test('linux') + api.platform('linux', 64)
