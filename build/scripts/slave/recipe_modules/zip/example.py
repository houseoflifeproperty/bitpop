# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'path',
  'platform',
  'step',
  'zip',
]

def GenSteps(api):
  # Prepare files.
  temp = api.path.mkdtemp('zip-example')
  yield api.step('touch a', ['touch', temp.join('a')])
  yield api.step('touch b', ['touch', temp.join('b')])
  yield api.path.makedirs('mkdirs', temp.join('sub', 'dir'))
  yield api.step('touch c', ['touch', temp.join('sub', 'dir', 'c')])

  # Build zip using 'zip.directory'.
  yield api.zip.directory('zipping', temp, temp.join('output.zip'))

  # Build a zip using ZipPackage api.
  package = api.zip.make_package(temp, temp.join('more.zip'))
  package.add_file(package.root.join('a'))
  package.add_file(package.root.join('b'))
  package.add_directory(package.root.join('sub'))
  yield package.zip('zipping more')

  # Coverage for 'output' property.
  yield api.step('report', ['echo', package.output])

  # Unzip the package.
  yield api.zip.unzip('unzipping', temp.join('output.zip'), temp.join('output'))
  # List unzipped content.
  yield api.step('listing', ['find'], cwd=temp.join('output'))
  # Clean up.
  yield api.path.rmtree('cleanup', temp)


def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    yield api.test(platform) + api.platform.name(platform)
