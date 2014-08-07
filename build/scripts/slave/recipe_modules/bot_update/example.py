# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'path',
  'properties',
]

def GenSteps(api):
  api.gclient.use_mirror = True

  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'src'
  soln.url = 'svn://svn.chromium.org/chrome/trunk/src'
  api.gclient.c = src_cfg
  force = True if api.properties.get('force') else False
  yield api.bot_update.ensure_checkout(force=force)


def GenTests(api):
  yield api.test('basic') + api.properties(
      mastername='chromium.linux',
      buildername='Linux Builder',
      slavename='totallyaslave-m1',
  )
  yield api.test('tryjob') + api.properties(
      mastername='tryserver.chromium',
      buildername='linux_rel',
      slavename='totallyaslave-c4',
      issue=12345,
      patchset=654321,
      patch_url='http://src.chromium.org/foo/bar'
  )
  yield api.test('tryjob_fail_patch') + api.properties(
      mastername='tryserver.chromium',
      buildername='linux_rel',
      slavename='totallyaslave-c4',
      issue=12345,
      patchset=654321,
      patch_url='http://src.chromium.org/foo/bar',
      fail_patch=True,
  )
  yield api.test('forced') + api.properties(
      mastername='experimental',
      buildername='Experimental Builder',
      slavename='somehost',
      force=1
  )
  yield api.test('off') + api.properties(
      mastername='experimental',
      buildername='Experimental Builder',
      slavename='somehost',
  )
