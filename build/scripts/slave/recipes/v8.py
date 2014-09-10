# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'step',
  'tryserver',
  'v8',
]


def GenSteps(api):
  v8 = api.v8
  v8.apply_bot_config(v8.BUILDERS)

  if api.tryserver.is_tryserver:
    v8.init_tryserver()

  if api.platform.is_win:
    api.chromium.taskkill()

  # On the branch builders, the gclient solution changes on every milestone.
  # If the sync fails, we nuke the build dir.
  v8.checkout(
      may_nuke=(api.tryserver.is_tryserver
                or api.properties.get('mastername') == 'client.v8.branches'),
      revert=api.tryserver.is_tryserver)

  if api.tryserver.is_tryserver:
    api.tryserver.maybe_apply_issue()

  if v8.needs_clang:
    v8.update_clang()
  v8.runhooks()
  api.chromium.cleanup_temp()

  if v8.c.nacl.update_nacl_sdk:
    v8.update_nacl_sdk()

  if v8.should_build:
    if api.tryserver.is_tryserver:
      v8.tryserver_compile(v8.tryserver_lkgr_fallback)
    else:
      v8.compile()

  if v8.should_upload_build:
    v8.upload_build()

  if v8.should_download_build:
    v8.download_build()

  if v8.should_test:
    v8.runtests()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in api.v8.BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config['testing'].get('parent_buildername') is None

      v8_config_kwargs = bot_config.get('v8_config_kwargs', {})
      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               parent_buildername=bot_config.get(
                                   'parent_buildername'),
                               revision='20123') +
        api.platform(bot_config['testing']['platform'],
                     v8_config_kwargs.get('TARGET_BITS', 64))
      )

      if mastername.startswith('tryserver'):
        test += (api.properties(
            revision='12345',
            patch_url='svn://svn-mirror.golo.chromium.org/patch'))

      yield test

  yield (
    api.test('try_compile_failure') +
    api.properties.tryserver(mastername='tryserver.v8',
                             buildername='v8_win_rel',
                             revision=None) +
    api.platform('win', 32) +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('branch_sync_failure') +
    api.properties.tryserver(mastername='client.v8.branches',
                             buildername='V8 Linux - trunk',
                             revision='20123') +
    api.platform('linux', 32) +
    api.step_data('gclient sync', retcode=1)
  )

  mastername = 'client.v8'
  buildername = 'V8 Linux - isolates'
  bot_config = api.v8.BUILDERS[mastername]['builders'][buildername]
  def TestFailures(wrong_results):
    suffix = "_wrong_results" if wrong_results else ""
    return (
      api.test('full_%s_%s_test_failures%s' % (_sanitize_nonalpha(mastername),
                                               _sanitize_nonalpha(buildername),
                                               suffix)) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             parent_buildername=bot_config.get(
                                 'parent_buildername')) +
      api.platform(bot_config['testing']['platform'],
                   v8_config_kwargs.get('TARGET_BITS', 64)) +
      api.v8(test_failures=True, wrong_results=wrong_results) +
      api.step_data('Check', retcode=1) +
      api.step_data('Check - flaky', retcode=1)
    )

  yield TestFailures(wrong_results=False)
  yield TestFailures(wrong_results=True)
  yield (
    api.test('full_%s_%s_flaky_test_failures' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           parent_buildername=bot_config.get(
                               'parent_buildername')) +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.step_data('Check - flaky', retcode=1)
  )

