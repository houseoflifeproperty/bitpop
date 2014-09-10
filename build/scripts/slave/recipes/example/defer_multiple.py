# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'step',
]

from slave import recipe_api

# Just for readability. Don't use global variables in real code.
API = None
def step(step_name):
  API.step(step_name, ['true'])

def deferrer(api):
  with api.step.defer_results():
    step('aggregated start')
    step('aggregated finish')

def normal(api):
  step('normal start')
  step('normal finish')

@recipe_api.composite_step
def composite_step(api):
  step('composite start')
  step('composite finish')

def GenSteps(api):
  global API
  API = api
  with api.step.defer_results():
    step('prelude')
    deferrer(api)
    normal(api)
    composite_step(api)
    step('clean up')


def GenTests(api):
  yield api.test('basic')

  yield (
      api.test('one_fail') +
      api.step_data('prelude', retcode=1)
    )

  yield (
      api.test('nested_aggregate_fail') +
      api.step_data('aggregated start', retcode=1)
    )

  yield (
      api.test('nested_normal_fail') +
      api.step_data('normal start', retcode=1)
    )

  yield (
      api.test('nested_comp_fail') +
      api.step_data('composite start', retcode=1)
    )
