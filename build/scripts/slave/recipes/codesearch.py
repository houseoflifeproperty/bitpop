# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'gsutil',
  'path',
  'properties',
  'python',
  'step',
]

def GenSteps(api):
  tarball_name = api.properties.get('tarball_name', 'src')
  tarball_name = tarball_name + '.tar.bz2'
  bucket_name = api.properties.get('bucket_name', 'chrome-codesearch')

  spec = api.gclient.make_config('android_bare')
  spec.target_os = ['android']
  s = spec.solutions[0]
  s.name = api.properties['repo_name']
  s.url = api.properties['repo_url']
  s.revision = 'refs/remotes/origin/master'
  yield api.gclient.checkout(spec)
  # Many following steps depends on checkout being set as 'src'
  api.path['checkout'] = api.path['slave_build'].join('src')
  api.chromium.set_config('codesearch')
  yield api.chromium.runhooks()

  yield api.step('archive source',
                 [api.path['build'].join('scripts',
                                 'slave', 'archive_source_codesearch.py'),
                  'src', 'src-internal', '-f', tarball_name])

  yield api.gsutil.upload(
      name='upload source tarball',
      source=api.path['slave_build'].join(tarball_name),
      bucket=bucket_name,
      dest=tarball_name
  )

def GenTests(api):
  yield (
    api.test('without-grok-index') +
    api.properties.generic(
      repo_name='src',
      repo_url='svn://svn-mirror.golo.chromium.org/chrome/trunk',
    )
  )

