# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This recipe can be used by components like v8 to verify blink tests with a
low false positive rate. Similar to a trybot, this recipe compares test
failures from a build with a current component revision with test failures
from a build with a pinned component revision.

Summary of the recipe flow:
1. Sync chromium to HEAD
2. Sync blink to HEAD
3. Sync component X to revision Y
4. Run blink tests
-> In case of failures:
5. Sync chromium to same revision as 1
6. Sync blink to same revision as 2
7. Sync component X to pinned revision from DEPS file
8. Run blink tests
-> If failures in 4 don't happen in 8, then revision Y reveals a problem not
   present in the pinned revision

Revision Y will be the revision property as provided by buildbot or HEAD (i.e.
in a forced build with no revision provided).
"""

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'raw_io',
  'step',
  'test_utils',
]


def V8Builder(config, bits, platform):
  chromium_configs = []
  if config == 'Debug':
    chromium_configs.append('v8_optimize_medium')
  return {
    'gclient_apply_config': ['show_v8_revision'],
    'chromium_apply_config': chromium_configs,
    'chromium_config_kwargs': {
      'BUILD_CONFIG': config,
      'TARGET_BITS': bits,
    },
    'component': {'path': 'src/v8', 'revision': 'bleeding_edge:%s'},
    'testing': {'platform': platform},
  }


BUILDERS = {
  'client.v8': {
    'builders': {
      'V8-Blink Win': V8Builder('Release', 32, 'win'),
      'V8-Blink Mac': V8Builder('Release', 32, 'mac'),
      'V8-Blink Linux 32': V8Builder('Release', 32, 'linux'),
      'V8-Blink Linux 64': V8Builder('Release', 64, 'linux'),
      'V8-Blink Linux 64 (dbg)': V8Builder('Debug', 64, 'linux'),
    },
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)

  # Sync chromium and blink to HEAD.
  api.chromium.set_config('blink',
                          **bot_config.get('chromium_config_kwargs', {}))
  api.gclient.set_config('blink_internal')

  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  # Sync component to current component revision.
  component_revision = api.properties.get('revision', 'HEAD')
  api.gclient.c.revisions[bot_config['component']['path']] = (
      bot_config['component']['revision'] % component_revision)

  # Ensure we remember the chromium revision.
  api.gclient.c.got_revision_mapping['src'] = 'got_cr_revision'

  api.step.auto_resolve_conflicts = True

  step_result = api.bot_update.ensure_checkout(force=True)

  api.chromium.runhooks()
  api.chromium.compile()

  api.chromium.runtest('webkit_unit_tests', xvfb=True)

  def component_pinned_fn(_failing_steps):
    bot_update_json = step_result.json.output
    api.gclient.c.revisions['src'] = str(
        bot_update_json['properties']['got_cr_revision'])
    api.gclient.c.revisions['src/third_party/WebKit'] = str(
        bot_update_json['properties']['got_webkit_revision'])
    # Reset component revision to the pinned revision from chromium's DEPS
    # for comparison.
    del api.gclient.c.revisions[bot_config['component']['path']]
    # Update without changing got_revision. The first sync is the revision
    # that is tested. The second is just for comparison. Setting got_revision
    # again confuses the waterfall's console view.
    api.bot_update.ensure_checkout(force=True, update_presentation=False)

    api.chromium.runhooks()
    api.chromium.compile()

  api.test_utils.determine_new_failures(
      api, [api.chromium.steps.BlinkTest(api)], component_pinned_fn)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.json.canned_test_output
  with_patch = 'webkit_tests (with patch)'
  without_patch = 'webkit_tests (without patch)'

  def properties(mastername, buildername):
    return (
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             revision='20123')
    )

  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                  _sanitize_nonalpha(buildername))
      tests = []
      for (pass_first, suffix) in ((True, '_pass'), (False, '_fail')):
        test = (
          properties(mastername, buildername) +
          api.platform(
              bot_config['testing']['platform'],
              bot_config.get(
                  'chromium_config_kwargs', {}).get('TARGET_BITS', 64)) +
          api.test(test_name + suffix) +
          api.step_data(with_patch, canned_test(passing=pass_first))
        )
        if not pass_first:
          test += api.step_data(
              without_patch, canned_test(passing=False, minimal=True))
        tests.append(test)

      for test in tests:
        yield test

  # This tests that if the first fails, but the second pass succeeds
  # that we fail the whole build.
  yield (
    api.test('minimal_pass_continues') +
    properties('client.v8', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(passing=False)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )


  # This tests what happens if something goes horribly wrong in
  # run-webkit-tests and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run-webkit-tests.
  yield (
    api.test('webkit_tests_unexpected_error') +
    properties('client.v8', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(passing=False, retcode=255))
  )

  # TODO(dpranke): crbug.com/357866 . This tests what happens if we exceed the
  # number of failures specified with --exit-after-n-crashes-or-times or
  # --exit-after-n-failures; the step should be considered a hard failure and
  # we shouldn't try to compare the lists of failing tests.
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run-webkit-tests.
  yield (
    api.test('webkit_tests_interrupted') +
    properties('client.v8', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(passing=False, retcode=130))
  )

  # This tests what happens if we don't trip the thresholds listed
  # above, but fail more tests than we can safely fit in a return code.
  # (this should be a soft failure and we can still retry w/o the patch
  # and compare the lists of failing tests).
  yield (
    api.test('too_many_failures_for_retcode') +
    properties('client.v8', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch,
                           canned_test(passing=False,
                                       num_additional_failures=125)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )
