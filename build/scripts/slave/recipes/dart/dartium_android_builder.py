# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'json',
  'path',
  'properties',
  'python',
]

def GenSteps(api):
  api.chromium_android.configure_from_properties(
      'dartium_builder',
      REPO_URL=api.properties.get('deps_url'),
      REPO_NAME='dartium.deps',
      BUILD_CONFIG='Release',
      INTERNAL=False)
  revision = api.properties.get('revision', 'HEAD')
  api.chromium_android.c.revision = revision
  api.chromium_android.c.revisions['src/dart'] = revision

  yield api.chromium_android.init_and_sync()
  yield api.chromium_android.clean_local_files()
  # TODO(iannucci): Remove when dartium syncs chromium to >= crrev.com/252649
  yield api.chromium_android.runhooks({'GYP_CROSSCOMPILE': "1"})
  yield api.chromium_android.compile(targets=['content_shell_apk'])
  yield api.chromium_android.cleanup_build()

  build_products_dir = \
      api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)
  yield api.python('dartium_test',
                   api.path['slave_build'].join('src', 'dart', 'tools',
                                                'bots', 'dartium_android.py'),
                   args=['--build-products-dir', build_products_dir])

def GenTests(api):
  yield (
      api.test('dartium_builder_basic') +
      api.properties.generic(
          revision='34567',
          buildername='dartium-builder',
          buildnumber=1337,
          deps_url='https://dart.googlecode.com/svn/trunk/deps/dartium.deps'))
