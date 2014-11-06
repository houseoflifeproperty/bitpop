# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'git',
  'json',
  'path',
  'properties',
  'python',
  'raw_io',
]


def GenSteps(api):
  # FIXME: Much of this code (bot_update, get upstream and commit patch so
  # presubmit_support doesn't freak out, run presubmit) is copied directly from
  # the run_presubmit.py recipe. We should instead share code!
  api.gclient.set_config('infra')
  res = api.bot_update.ensure_checkout(force=True, patch_root='infra')
  upstream = res.json.output['properties'].get('got_revision')
  api.git('-c', 'user.email=commit-bot@chromium.org',
          '-c', 'user.name=The Commit Bot',
          'commit', '-a', '-m', 'Committed patch',
          name='commit git patch',
          cwd=api.path['checkout'])
  api.gclient.runhooks()

  # Grab a list of changed files.
  result = api.git(
      'diff', '--name-only', 'HEAD', 'HEAD~',
      name='get change list',
      cwd=api.path['checkout'],
      stdout=api.raw_io.output())
  files = result.stdout.splitlines()

  if not all(f.startswith('go/') for f in files):
    api.python('test.py', api.path['checkout'].join('test.py'))

  if any(f.startswith('go/') for f in files):
    # Note: env.py knows how to expand 'python' into sys.executable.
    api.python(
        'go test.py', api.path['checkout'].join('go', 'env.py'),
        ['python', api.path['checkout'].join('go', 'test.py')])

  api.python('presubmit',
      api.path['depot_tools'].join('presubmit_support.py'),
      ['--root', api.path['checkout'],
      '--commit',
      '--verbose', '--verbose',
      '--issue', api.properties['issue'],
      '--patchset', api.properties['patchset'],
      '--skip_canned', 'CheckRietveldTryJobExecution',
      '--skip_canned', 'CheckTreeIsOpen',
      '--skip_canned', 'CheckBuildbotPendingBuilds',
      '--rietveld_url', api.properties['rietveld'],
      '--rietveld_email', '',  # activates anonymous mode
      '--rietveld_fetch',
      '--upstream', upstream,
  ])


def GenTests(api):
  def diff(*files):
    return api.step_data(
        'get change list', api.raw_io.stream_output('\n'.join(files)))

  yield (
    api.test('basic') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='infra_tester',
        repo_name='infra') +
    diff('infra/stuff.py', 'go/src/infra/stuff.go')
  )

  yield (
    api.test('only_go') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='infra_tester',
        repo_name='infra') +
    diff('go/src/infra/stuff.go')
  )

  yield (
    api.test('only_python') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='infra_tester',
        repo_name='infra') +
    diff('infra/stuff.py')
  )
