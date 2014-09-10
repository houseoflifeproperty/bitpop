# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'path',
  'properties',
  'tryserver',
]


def GenSteps(api):
  api.path['checkout'] = api.path['slave_build']
  api.tryserver.maybe_apply_issue()


def GenTests(api):
  yield (api.test('with_svn_patch') +
         api.properties(patch_url='svn://checkout.url'))

  yield (api.test('with_git_patch') +
         api.properties(
              patch_storage='git',
              patch_repo_url='http://patch.url/',
              patch_ref='johndoe#123.diff'))

  yield (api.test('with_rietveld_patch') +
         api.properties.tryserver())

  yield (api.test('with_wrong_patch'))
