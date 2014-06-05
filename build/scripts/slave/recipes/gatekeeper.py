# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Specifies how to launch the gatekeeper."""

DEPS = [
  'path',
  'step',
]

def GenSteps(api):
  yield api.step('gatekeeper_launch',
                 [api.path['build'].join('scripts', 'slave',
                                         'gatekeeper_launch.py')])

def GenTests(api):
  yield api.test('basic')
