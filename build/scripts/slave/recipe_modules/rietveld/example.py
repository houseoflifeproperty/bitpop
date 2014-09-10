# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'path',
  'properties',
  'step',
  'rietveld',
]

def GenSteps(api):
  api.path['checkout'] = api.path['slave_build']
  api.rietveld.apply_issue('foo', 'bar', authentication='oauth2')


def GenTests(api):
  yield (api.test('basic')
         + api.properties(issue=1,
                          patchset=1,
                          rietveld='http://review_tool.url')
         )
