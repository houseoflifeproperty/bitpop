# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
  'python',
]

def GenSteps(api):
  api.gclient.set_config('infra')
  api.gclient.checkout()
  api.gclient.runhooks()
  api.python('test.py', api.path['checkout'].join('test.py'))


def GenTests(api):
  yield api.test('basic')
