# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running tests for WebRTC stand-alone.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
  'tryserver',
  'webrtc',
]


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.webrtc.BUILDERS.get(mastername, {})
  master_settings = master_dict.get('settings', {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  bot_type = bot_config.get('bot_type', 'builder_tester')
  assert bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                      (buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  recipe_config = api.webrtc.RECIPE_CONFIGS.get(recipe_config_name)
  assert recipe_config, ('Cannot find recipe_config "%s" for builder "%r".' %
                         (recipe_config_name, buildername))

  api.webrtc.set_config(recipe_config['webrtc_config'],
                        PERF_CONFIG=master_settings.get('PERF_CONFIG'),
                        **bot_config.get('webrtc_config_kwargs', {}))
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  # Needed for the multiple webcam check steps to get unique names.
  api.step.auto_resolve_conflicts = True

  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')

  step_result = api.gclient.checkout()
  # Whatever step is run right before this line needs to emit got_revision.
  got_revision = step_result.presentation.properties['got_revision']

  if api.tryserver.is_tryserver:
    api.tryserver.maybe_apply_issue()

  api.chromium.runhooks()
  if api.chromium.c.project_generator.tool == 'gn':
    api.chromium.run_gn()
    api.chromium.compile(targets=['all'])
  else:
    api.chromium.compile()

  if api.chromium.c.gyp_env.GYP_DEFINES.get('syzyasan', 0) == 1:
    api.chromium.apply_syzyasan()

  test_suite = recipe_config.get('test_suite')
  if test_suite and bot_type in ('builder_tester', 'tester'):
    api.webrtc.runtests(test_suite, got_revision)

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  def generate_builder(mastername, buildername, bot_config, revision,
                       suffix=None):
    suffix = suffix or ''
    bot_type = bot_config.get('bot_type', 'builder_tester')
    if bot_type in ('builder', 'builder_tester'):
      assert bot_config.get('parent_buildername') is None, (
          'Unexpected parent_buildername for builder %r on master %r.' %
              (buildername, mastername))

    webrtc_config_kwargs = bot_config.get('webrtc_config_kwargs', {})
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties(mastername=mastername,
                     buildername=buildername,
                     slavename='slavename') +
      api.platform(bot_config['testing']['platform'],
                   webrtc_config_kwargs.get('TARGET_BITS', 64))
    )
    if revision:
      test += api.properties(revision=revision)
    if mastername.startswith('tryserver'):
      test += api.properties(patch_url='try_job_svn_patch')
    return test

  for mastername in ('client.webrtc', 'client.webrtc.fyi', 'tryserver.webrtc'):
    master_config = api.webrtc.BUILDERS[mastername]
    for buildername, bot_config in master_config['builders'].iteritems():
      if bot_config['recipe_config'] == 'webrtc_android_apk':
        continue
      yield generate_builder(mastername, buildername, bot_config,
                             revision='12345')

  # Forced build (not specifying any revision).
  mastername = 'client.webrtc'
  buildername = 'Linux64 Debug'
  bot_config = api.webrtc.BUILDERS[mastername]['builders'][buildername]
  yield generate_builder(mastername, buildername, bot_config, revision=None,
                         suffix='_forced')
