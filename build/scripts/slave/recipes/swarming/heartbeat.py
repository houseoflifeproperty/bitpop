# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Swarming heart beat recipe: runs a dummy job on the prod Swarming instance to
ensure it is working properly.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall
"""

DEPS = [
  'python',
  'properties',
  'path',
  'swarming',
  'swarming_client',
]


def GenSteps(api):
  branch = 'stable'
  if api.properties.get('target_environment') == 'canary':
    branch = 'master'
  api.swarming_client.checkout(branch, can_fail_build=False)
  api.swarming.check_client_version()
  script = api.path['build'].join(
      'scripts', 'slave', 'swarming', 'job_runs_fine.py')
  args = []
  if api.properties.get('target_environment') == 'canary':
    args = ['--canary']
  api.python('job_runs_fine.py', script, args=args, cwd=api.path['slave_build'])


def GenTests(api):
  yield (
    api.test('heartbeat') +
    api.properties.scheduled()
  )
  yield (
    api.test('heartbeat_canary') +
    api.properties.scheduled(target_environment='canary')
  )
