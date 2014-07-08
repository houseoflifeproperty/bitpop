# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gsutil',
  'path',
]


def GenSteps(api):
  """Move things around in a loop!"""
  local_file = api.path['slave_build'].join('boom')
  bucket = 'chromium-recipe-test'
  cloud_file = 'some/random/path/to/boom'
  yield api.gsutil.upload(local_file, bucket, cloud_file)

  yield api.gsutil(['cp',
                    'gs://chromium-recipe-test/some/random/path/**',
                    'gs://chromium-recipe-test/staging'])

  yield api.gsutil.download_url(
      'http://storage.cloud.google.com/' + bucket + '/' + cloud_file,
      local_file,
      name='gsutil download url')

  new_cloud_file = 'staging/to/boom'
  new_local_file = api.path['slave_build'].join('erang')
  yield api.gsutil.download(bucket, new_cloud_file, new_local_file)


def GenTests(api):
  yield api.test('basic')
