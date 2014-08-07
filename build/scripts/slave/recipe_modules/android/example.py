# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'android',
  'properties',
]

def GenSteps(api):
  api.android.set_config('AOSP')
  api.android.c.lunch_flavor = 'nakasi-userdebug'
  api.android.c.repo.url = (
    'https://android.googlesource.com/platform/manifest')
  api.android.c.repo.branch = 'master'

  yield api.android.sync_chromium()

  yield api.android.repo_init_steps()
  yield api.android.repo_sync_steps()
  yield api.android.update_defaut_props_step({'ro.adb.secure': '0'})

  yield api.android.rsync_chromium_into_android_tree_step()

  make_vars = {'CC': 'foo', 'CXX': 'bar'}
  yield api.android.compile_step(
      build_tool='make-android',
      step_name='compile android',
      targets=['droid'],
      defines=make_vars)

def GenTests(api):
  yield api.test('basic') + api.properties(
      mastername='chromium.linux',
      buildername='Android Builder',
      slavename='totallyanandroid-m1',
      revision='123456',
  )

