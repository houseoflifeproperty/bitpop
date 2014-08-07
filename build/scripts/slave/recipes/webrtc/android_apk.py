# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'base_android',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'step_history',
  'tryserver',
  'webrtc',
]


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.webrtc.BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name %r for master %r.' %
                      (buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  recipe_config = api.webrtc.RECIPE_CONFIGS.get(recipe_config_name)
  assert recipe_config, ('Cannot find recipe_config "%s" for builder "%r".' %
                         (recipe_config_name, buildername))

  # The infrastructure team has recommended not to use git yet on the
  # bots, but it's very nice to have when testing locally.
  # To use, pass "use_git=True" as an argument to run_recipe.py.
  use_git = api.properties.get('use_git', False)

  api.webrtc.set_config(recipe_config['webrtc_config'],
                        GIT_MODE=use_git,
                        **bot_config.get('webrtc_config_kwargs', {}))
  if api.tryserver.is_tryserver:
    api.webrtc.apply_config('webrtc_android_apk_try_builder')

  bot_type = bot_config.get('bot_type', 'builder_tester')
  does_build = bot_type in ('builder', 'builder_tester')
  does_test = bot_type in ('builder_tester', 'tester')

  # Replace src/third_party/webrtc with the specified revision and force the
  # Chromium code to sync ToT.
  s = api.gclient.c.solutions
  s[0].revision = 'HEAD'

  if bot_type == 'tester':
    webrtc_revision = api.properties.get('parent_got_revision')
    assert webrtc_revision, (
       'Testers cannot be forced without providing revision information. Please'
       'select a previous build and click [Rebuild] or force a build for a '
       'Builder instead (will trigger new runs for the testers).')
  else:
    # For forced builds, revision is empty, in which case we sync HEAD.
    webrtc_revision = api.properties.get('revision', 'HEAD')

  s[0].custom_vars['webrtc_revision'] = webrtc_revision

  # TODO(iannucci): Support webrtc.apply_svn_patch with bot_update
  # crbug.com/376122
  yield api.bot_update.ensure_checkout()
  bot_update_mode = api.step_history.last_step().json.output['did_run']
  if not bot_update_mode:
    yield api.gclient.checkout()

  # Whatever step is run right before this line needs to emit got_revision.
  update_step = api.step_history.last_step()
  got_revision = update_step.presentation.properties['got_revision']

  if not bot_update_mode:
    if does_build and api.tryserver.is_tryserver:
      yield api.webrtc.apply_svn_patch()

  if does_build:
    yield api.base_android.envsetup()

  # WebRTC Android APK testers also have to run the runhooks, since test
  # resources are currently downloaded during this step.
  yield api.base_android.runhooks()

  yield api.chromium.cleanup_temp()
  if does_build:
    yield api.base_android.compile()

  if bot_type == 'builder':
    yield api.webrtc.package_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']], got_revision)

  if bot_type == 'tester':
    yield api.webrtc.extract_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']], got_revision)

  if does_test:
    yield api.chromium_android.common_tests_setup_steps()
    for test in api.webrtc.ANDROID_APK_TESTS:
      yield api.base_android.test_runner(test)

    yield api.chromium_android.common_tests_final_steps()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  def generate_builder(mastername, buildername, bot_config, revision=None,
                       parent_got_revision=None, suffix=None):
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
                     slavename='fake_slavename',
                     parent_buildername=bot_config.get('parent_buildername'),
                     TARGET_PLATFORM=webrtc_config_kwargs['TARGET_PLATFORM'],
                     TARGET_ARCH=webrtc_config_kwargs['TARGET_ARCH'],
                     TARGET_BITS=webrtc_config_kwargs['TARGET_BITS'],
                     BUILD_CONFIG=webrtc_config_kwargs['BUILD_CONFIG']) +
      api.platform(bot_config['testing']['platform'],
                   webrtc_config_kwargs.get('TARGET_BITS', 64))
    )
    if bot_type in ('builder', 'builder_tester'):
      test += api.step_data('envsetup',
          api.json.output({
              'FOO': 'bar',
              'GYP_DEFINES': 'my_new_gyp_def=aaa',
          }))

    if revision:
      test += api.properties(revision=revision)
    if bot_type == 'tester':
      parent_rev = parent_got_revision or revision
      test += api.properties(parent_got_revision=parent_rev)

    if mastername.startswith('tryserver'):
      test += api.properties(patch_url='try_job_svn_patch')

    return test

  for mastername in ('client.webrtc', 'tryserver.webrtc'):
    master_config = api.webrtc.BUILDERS[mastername]
    for buildername, bot_config in master_config['builders'].iteritems():
      if bot_config['recipe_config'] != 'webrtc_android_apk':
        continue
      yield generate_builder(mastername, buildername, bot_config,
                             revision='12345')

  # Forced build (no revision information).
  mastername = 'client.webrtc'
  buildername = 'Android Chromium-APK Builder'
  bot_config = api.webrtc.BUILDERS[mastername]['builders'][buildername]
  yield generate_builder(mastername, buildername, bot_config, revision=None,
                         suffix='_forced')

  buildername = 'Android Chromium-APK Tests (KK Nexus5)'
  bot_config = api.webrtc.BUILDERS[mastername]['builders'][buildername]
  yield generate_builder(mastername, buildername, bot_config, revision=None,
                         parent_got_revision='12345', suffix='_forced')
