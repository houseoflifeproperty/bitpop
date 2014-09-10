# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'gsutil',
  'path',
  'properties',
  'step',
]


def GenSteps(api):
  kwargs = {}
  kwargs['TARGET_PLATFORM'] = 'android'
  kwargs['TARGET_ARCH'] = 'arm'
  api.chromium.set_config('chromium', **kwargs)
  api.gclient.apply_config('android')
  step_result = api.bot_update.ensure_checkout()
  # Whatever step is run right before this line needs to emit got_revision.
  got_revision = step_result.presentation.properties['got_revision']

  harness_file = 'telemetry-%s.zip' % got_revision
  harness_path = api.path.mkdtemp('telemetry-harness')

  api.step('create harness archive', [
                   api.path['checkout'].join(
                       'tools', 'telemetry', 'build',
                       'generate_telemetry_harness.sh'),
                   harness_path.join(harness_file),
                 ]
  )

  bucket = 'chromium-telemetry'
  cloud_file = 'snapshots/%s' % harness_file
  api.gsutil.upload(harness_path.join(harness_file), bucket, cloud_file,
                          link_name='Telemetry r%s' % got_revision)
  api.gsutil.copy(bucket, cloud_file, bucket, 'snapshots/telemetry.zip',
                        link_name='Telemetry latest')
  api.path.rmtree('remove harness temp directory', harness_path)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.generic(
          mastername='chromium.lkgr',
          buildername='Telemetry Harness Upload')
  )
