# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'isolate',
  'path',
  'python',
  'raw_io',
  'step',
  'step_history',
  'swarming',
  'swarming_client',
]


def GenSteps(api):
  # Checkout swarming client.
  yield api.swarming_client.checkout('master')

  # Ensure swarming_client version is fresh enough.
  yield api.swarming.check_client_version()

  # Configure isolate & swarming modules (this is optional).
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  api.swarming.swarming_server = 'https://chromium-swarm-dev.appspot.com'
  api.swarming.profile = True
  api.swarming.verbose = True
  api.swarming.task_priority = 30

  # Create a temp dir to put *.isolated files into.
  temp_dir = api.path.mkdtemp('hello_isolated_world')

  # Prepare a bunch of swarming tasks to run hello_world on multiple platforms.
  tasks = []
  for platform in ('win', 'linux', 'mac'):
    # Isolate example hello_world.isolate from swarming client repo.
    # TODO(vadimsh): Add a thin wrapper around isolate.py to 'isolate' module?
    yield api.python(
        'archive for %s' % platform,
        api.swarming_client.path.join('isolate.py'),
        [
          'archive',
          '--isolate', api.swarming_client.path.join(
              'example', 'payload', 'hello_world.isolate'),
          '--isolated', temp_dir.join('hello_world.isolated'),
          '--isolate-server', api.isolate.isolate_server,
          '--config-variable', 'OS', platform,
          '--verbose',
        ], stdout=api.raw_io.output())
    # TODO(vadimsh): Pass result from isolate.py though --output-json option.
    isolated_hash = api.step_history.last_step().stdout.split()[0].strip()

    # Create a task to run the isolated file on swarming, set OS dimension.
    task = api.swarming.task('hello_world', isolated_hash, make_unique=True)
    task.dimensions['os'] = api.swarming.platform_to_os_dimension(platform)
    task.env['TESTING'] = '1'
    tasks.append(task)

  # Launch all tasks.
  yield api.swarming.trigger(tasks)

  # Recipe can do something useful here locally while tasks are
  # running on swarming.
  yield api.step('local step', ['echo', 'running something locally'])

  # Wait for all tasks to complete.
  yield api.swarming.collect(tasks)

  # Cleanup.
  yield api.path.rmtree('remove temp dir', temp_dir)


def GenTests(api):
  yield (
      api.test('basic') +
      api.step_data(
          'archive for win',
          stdout=api.raw_io.output('hash_for_win hello_world.isolated')) +
      api.step_data(
          'archive for linux',
          stdout=api.raw_io.output('hash_for_linux hello_world.isolated')) +
      api.step_data(
          'archive for mac',
          stdout=api.raw_io.output('hash_for_mac hello_world.isolated')))
