# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building Chromium and running WebRTC-specific tests with special
# requirements that doesn't allow them to run in the main Chromium waterfalls.
# Also provide a set of FYI bots that builds Chromium with WebRTC ToT to provide
# pre-roll test results.

DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step_history',
  'webrtc',
]


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.webrtc.BUILDERS.get(mastername, {})
  master_settings = master_dict.get('settings', {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name "%r" for master "%r".' %
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
                        PERF_CONFIG=master_settings.get('PERF_CONFIG'),
                        **bot_config.get('webrtc_config_kwargs', {}))
  api.chromium.set_config(recipe_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  api.gclient.set_config(recipe_config['gclient_config'], GIT_MODE=use_git)
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if api.platform.is_win:
    yield api.chromium.taskkill()

  bot_type = bot_config.get('bot_type', 'builder_tester')

  # The chromium.webrtc.fyi master is used as an early warning system to catch
  # WebRTC specific errors before they get rolled into Chromium's DEPS.
  # Therefore this waterfall needs to build src/third_party/webrtc with WebRTC
  # ToT and use the Chromium HEAD. The revision poller is passing a WebRTC
  # revision for these recipes.
  if mastername == 'chromium.webrtc.fyi':
    s = api.gclient.c.solutions
    s[0].revision = 'HEAD'

    if bot_type == 'tester':
      webrtc_revision = api.properties.get('parent_got_revision')
      assert webrtc_revision, (
         'Testers cannot be forced without providing revision information. '
         'Please select a previous build and click [Rebuild] or force a build '
         'for a Builder instead (will trigger new runs for the testers).')
    else:
      # For forced builds, revision is empty, in which case we sync HEAD.
      webrtc_revision = api.properties.get('revision', 'HEAD')

    s[0].custom_vars['webrtc_revision'] = webrtc_revision

  # Bot Update re-uses the gclient configs.
  yield api.bot_update.ensure_checkout(),
  if not api.step_history.last_step().json.output['did_run']:
    yield api.gclient.checkout(),
  # Whatever step is run right before this line needs to emit got_revision.
  update_step = api.step_history.last_step()
  got_revision = update_step.presentation.properties['got_revision']


  if not bot_config.get('disable_runhooks'):
    yield api.chromium.runhooks()

  yield api.chromium.cleanup_temp()

  # Instead of yielding single steps or groups of steps, yield all at the end.
  steps = []

  if bot_type in ('builder', 'builder_tester'):
    compile_targets = recipe_config.get('compile_targets', [])
    steps.append(api.chromium.compile(targets=compile_targets))
    if mastername == 'chromium.webrtc.fyi':
      steps.append(api.webrtc.sizes(got_revision))

  if bot_type == 'builder':
    steps.append(api.webrtc.package_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']], got_revision))

  if bot_type == 'tester':
    # Ensure old build directory is not used is by removing it.
    steps.append(api.path.rmtree(
        'build directory',
        api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)))

    steps.append(api.webrtc.extract_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']], got_revision))

  if bot_type in ('builder_tester', 'tester'):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      steps.append(api.chromium_android.common_tests_setup_steps())
      steps.append(api.chromium_android.run_test_suite(
          'content_browsertests',
          gtest_filter='WebRtc*'))
      steps.append(api.chromium_android.common_tests_final_steps())
    else:
      test_steps = api.webrtc.runtests(recipe_config.get('test_suite'),
                                       revision=got_revision)
      steps.extend(api.chromium.setup_tests(bot_type, test_steps))

  yield steps


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
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             parent_buildername=bot_config.get(
                                 'parent_buildername')) +
      api.platform(bot_config['testing']['platform'],
                   bot_config.get(
                       'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
    )
    if revision:
      test += api.properties(revision=revision)
    if bot_type == 'tester':
      parent_rev = parent_got_revision or revision
      test += api.properties(parent_got_revision=parent_rev)
    return test

  for mastername in ('chromium.webrtc', 'chromium.webrtc.fyi'):
    master_config = api.webrtc.BUILDERS[mastername]
    for buildername, bot_config in master_config['builders'].iteritems():
      revision = '12345' if mastername == 'chromium.webrtc.fyi' else '321321'
      yield generate_builder(mastername, buildername, bot_config, revision)

  # Forced build (not specifying any revision).
  mastername = 'chromium.webrtc'
  buildername = 'Linux Builder'
  bot_config = api.webrtc.BUILDERS[mastername]['builders'][buildername]
  yield generate_builder(mastername, buildername, bot_config, revision=None,
                         suffix='_forced')

  # Periodic scheduler triggered builds also don't contain revision.
  mastername = 'chromium.webrtc.fyi'
  buildername = 'Win Builder'
  bot_config = api.webrtc.BUILDERS[mastername]['builders'][buildername]
  yield generate_builder(mastername, buildername, bot_config, revision=None,
                         suffix='_periodic_triggered')

  # Testers gets got_revision value from builder passed as parent_got_revision.
  buildername = 'Win7 Tester'
  bot_config = api.webrtc.BUILDERS[mastername]['builders'][buildername]
  yield generate_builder(mastername, buildername, bot_config, revision=None,
                         parent_got_revision='12345',
                         suffix='_periodic_triggered')
