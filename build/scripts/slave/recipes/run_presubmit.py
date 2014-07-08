# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'git',
  'json',
  'path',
  'properties',
  'rietveld',
  'step',
  'step_history',
]

def GenSteps(api):
  root = api.rietveld.calculate_issue_root()

  # TODO(iannucci): Pass the build repo info directly via properties
  repo_name = api.properties['repo_name']

  api.gclient.set_config(repo_name)
  api.step.auto_resolve_conflicts = True

  yield api.bot_update.ensure_checkout()
  bot_update_step = api.step_history.last_step()
  bot_update_mode = bot_update_step.json.output['did_run']
  if not bot_update_mode:
    yield api.gclient.checkout(
        revert=True, can_fail_build=False, abort_on_failure=False)
    for step in api.step_history.values():
      if step.retcode != 0:
        yield (
          api.path.rmcontents('slave build directory', api.path['slave_build']),
          api.gclient.checkout(revert=False),
        )
        break
    upstream = ''
  else:
    upstream = bot_update_step.json.output['properties'].get(
        'got_revision_git') or ''

  # Run this regardless of whether bot_update is on or off.
  spec = api.gclient.c
  if spec.solutions[0].url.endswith('.git'):
    yield (
        api.git('config', 'user.email', 'commit-bot@chromium.org'),
        api.git('config', 'user.name', 'The Commit Bot'),
        api.git('clean', '-xfq')
    )

  if not bot_update_mode:
    yield api.rietveld.apply_issue(root)

  yield api.step('presubmit', [
    api.path['depot_tools'].join('presubmit_support.py'),
    '--root', api.path['checkout'].join(root),
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
    '--upstream', upstream,  # '' if not in bot_update mode.
    '--trybot-json', api.json.output()])


def GenTests(api):
  for repo_name in ['blink', 'tools_build', 'chromium']:
    extra = {}
    if 'blink' in repo_name:
      extra['root'] = 'src/third_party/WebKit'
    elif 'tools_build' in repo_name:
      extra['root'] = 'build'

    yield (
      api.test(repo_name) +
      api.properties.tryserver(mastername='tryserver.chromium',
                               buildername='chromium_presubmit',
                               repo_name=repo_name, **extra) +
      api.step_data('presubmit', api.json.output([['chromium_presubmit',
                                                   ['compile']]]))
    )

  yield (
    api.test('gclient_retry') +
    api.properties.tryserver(repo_name='chromium') +
    api.step_data('gclient revert', retcode=1) +
    api.step_data('presubmit', api.json.output([['linux_rel', ['compile']]]))
  )
