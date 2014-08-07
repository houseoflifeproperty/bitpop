# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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
  'rietveld',
  'step',
  'step_history',
  'test_utils',
]


BUILDERS = {
  'tryserver.blink': {
    'builders': {
      'linux_blink_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_bot_update': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_no_bot_update': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': True,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_oilpan_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_blink_oilpan_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'testing': {
          'platform': 'linux',
        },
      },
      'mac_blink_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_oilpan_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_blink_oilpan_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'mac',
        },
      },
      'win_blink_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': True,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_oilpan_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
      'win_blink_oilpan_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'compile_only': False,
        'testing': {
          'platform': 'win',
        },
      },
    },
  },
  'tryserver.v8': {
    'builders': {
      'v8_linux_layout_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'compile_only': False,
        'v8_blink_flavor': True,
        'root_override': 'v8',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}


def GenSteps(api):
  class BlinkTest(api.test_utils.Test):
    name = 'webkit_tests'

    def __init__(self):
      self.results_dir = api.path['slave_build'].join('layout-test-results')
      self.layout_test_wrapper = api.path['build'].join(
          'scripts', 'slave', 'chromium', 'layout_test_wrapper.py')

    def run(self, suffix):
      args = ['--target', api.chromium.c.BUILD_CONFIG,
              '-o', self.results_dir,
              '--build-dir', api.chromium.c.build_dir,
              '--json-test-results', api.json.test_results(add_json_log=False)]
      if suffix == 'without patch':
        test_list = "\n".join(self.failures('with patch'))
        args.extend(['--test-list', api.raw_io.input(test_list),
                     '--skipped', 'always'])

      if 'oilpan' in api.properties['buildername']:
        args.extend(['--additional-expectations',
                     api.path['checkout'].join('third_party', 'WebKit',
                                               'LayoutTests',
                                               'OilpanExpectations')])

      def followup_fn(step_result):
        r = step_result.json.test_results
        p = step_result.presentation

        p.step_text += api.test_utils.format_step_text([
          ['unexpected_flakes:', r.unexpected_flakes.keys()],
          ['unexpected_failures:', r.unexpected_failures.keys()],
          ['Total executed: %s' % r.num_passes],
        ])

        if r.unexpected_flakes or r.unexpected_failures:
          p.status = 'WARNING'
        else:
          p.status = 'SUCCESS'

      yield api.chromium.runtest(self.layout_test_wrapper,
                                 args,
                                 name=self._step_name(suffix),
                                 can_fail_build=False,
                                 followup_fn=followup_fn)

      if suffix == 'with patch':
        buildername = api.properties['buildername']
        buildnumber = api.properties['buildnumber']
        def archive_webkit_tests_results_followup(step_result):
          base = (
            "https://storage.googleapis.com/chromium-layout-test-archives/%s/%s"
            % (buildername, buildnumber))

          step_result.presentation.links['layout_test_results'] = (
              base + '/layout-test-results/results.html')
          step_result.presentation.links['(zip)'] = (
              base + '/layout-test-results.zip')

        archive_layout_test_results = api.path['build'].join(
            'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

        yield api.python(
          'archive_webkit_tests_results',
          archive_layout_test_results,
          [
            '--results-dir', self.results_dir,
            '--build-dir', api.chromium.c.build_dir,
            '--build-number', buildnumber,
            '--builder-name', buildername,
            '--gs-bucket', 'gs://chromium-layout-test-archives',
          ] + api.json.property_args(),
          followup_fn=archive_webkit_tests_results_followup
        )

    def has_valid_results(self, suffix):
      step = api.step_history[self._step_name(suffix)]
      # TODO(dpranke): crbug.com/357866 - note that all comparing against
      # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
      # or abnormally; it does not tell us how many failures there actually
      # were, which might be much higher (up to 5000 diffs, where we
      # would bail out early with --exit-after-n-failures) or lower
      # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
      # which case the retcode is actually 130
      return (step.json.test_results.valid and
              step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS)

    def failures(self, suffix):
      sn = self._step_name(suffix)
      return api.step_history[sn].json.test_results.unexpected_failures

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)

  api.chromium.set_config('blink',
                          **bot_config.get('chromium_config_kwargs', {}))
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('blink_internal')
  if bot_config.get('v8_blink_flavor'):
    api.gclient.apply_config('v8_blink_flavor')
    api.gclient.apply_config('show_v8_revision')
    if api.properties['revision']:
      api.gclient.c.revisions['src/v8'] = api.properties['revision']
  api.step.auto_resolve_conflicts = True

  if 'oilpan' in buildername:
    api.chromium.apply_config('oilpan')

  webkit_lint = api.path['build'].join('scripts', 'slave', 'chromium',
                                       'lint_test_files_wrapper.py')
  webkit_python_tests = api.path['build'].join('scripts', 'slave', 'chromium',
                                               'test_webkitpy_wrapper.py')

  root = bot_config.get('root_override', api.rietveld.calculate_issue_root())

  yield api.bot_update.ensure_checkout()
  # The first time we run bot update, remember if bot_update mode is on or off.
  bot_update_mode = api.step_history.last_step().json.output['did_run']
  if not bot_update_mode:
    yield api.gclient.checkout(
        revert=True, can_fail_build=False, abort_on_failure=False)
    for step in api.step_history.values():
      if step.retcode != 0:
        # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
        yield (
          api.path.rmcontents('slave build directory', api.path['slave_build']),
          api.gclient.checkout(),
        )
        break
    yield api.rietveld.apply_issue(root)

  yield (
    api.chromium.runhooks(),
    api.chromium.compile(abort_on_failure=False, can_fail_build=False),
  )

  if api.step_history['compile'].retcode != 0:
    # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
    if api.platform.is_win:
      yield api.chromium.taskkill()
    yield api.path.rmcontents('slave build directory', api.path['slave_build'])
    if bot_update_mode:
      yield api.bot_update.ensure_checkout()
    else:
      yield (
        api.gclient.checkout(revert=False),
        api.rietveld.apply_issue(root),
      )
    yield (
      api.chromium.runhooks(),
      api.chromium.compile(),
    )

  if not bot_config['compile_only']:
    yield (
      api.python('webkit_lint', webkit_lint, [
        '--build-dir', api.path['checkout'].join('out'),
        '--target', api.chromium.c.BUILD_CONFIG
      ]),
      api.python('webkit_python_tests', webkit_python_tests, [
        '--build-dir', api.path['checkout'].join('out'),
        '--target', api.chromium.c.BUILD_CONFIG,
      ]),
      api.chromium.runtest('webkit_unit_tests', xvfb=True),
      api.chromium.runtest('blink_platform_unittests'),
      api.chromium.runtest('blink_heap_unittests'),
      api.chromium.runtest('wtf_unittests'),
    )

  if not bot_config['compile_only']:
    def deapply_patch_fn(_failing_steps):
      if bot_update_mode:
        yield api.bot_update.ensure_checkout(patch=False, always_run=True)
      else:
        yield api.gclient.checkout(revert=True, always_run=True)

      yield (
        api.chromium.runhooks(always_run=True),
        api.chromium.compile(always_run=True),
      )

    yield api.test_utils.determine_new_failures([BlinkTest()], deapply_patch_fn)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.json.canned_test_output
  with_patch = 'webkit_tests (with patch)'
  without_patch = 'webkit_tests (without patch)'

  def properties(mastername, buildername, **kwargs):
    return api.properties.tryserver(mastername=mastername,
                                    buildername=buildername,
                                    root='src/third_party/WebKit',
                                    **kwargs)

  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                  _sanitize_nonalpha(buildername))
      tests = []
      if bot_config['compile_only']:
        tests.append(api.test(test_name))
      else:
        for pass_first in (True, False):
          test = (
            api.test(test_name + ('_pass' if pass_first else '_fail')) +
            api.step_data(with_patch, canned_test(passing=pass_first))
          )
          if not pass_first:
            test += api.step_data(
                without_patch, canned_test(passing=False, minimal=True))
          tests.append(test)

      for test in tests:
        test += (
          properties(mastername, buildername) +
          api.platform(bot_config['testing']['platform'],
                       bot_config.get(
                           'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
        )

        yield test

  # This tests that if the first fails, but the second pass succeeds
  # that we fail the whole build.
  yield (
    api.test('minimal_pass_continues') +
    properties('tryserver.blink', 'linux_blink_rel') +
    api.override_step_data(with_patch, canned_test(passing=False)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )

  yield (
    api.test('gclient_revert_nuke') +
    properties('tryserver.blink', 'linux_blink_no_bot_update') +
    api.step_data('gclient revert', retcode=1) +
    api.override_step_data(with_patch, canned_test(passing=True, minimal=True))
  )

  yield (
    api.test('preamble_test_failure') +
    properties('tryserver.blink', 'linux_blink_rel') +
    api.step_data('webkit_unit_tests', retcode=1)
  )

  # This tests what happens if something goes horribly wrong in
  # run-webkit-tests and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run-webkit-tests.
  yield (
    api.test('webkit_tests_unexpected_error') +
    properties('tryserver.blink', 'linux_blink_rel') +
    api.override_step_data(with_patch, canned_test(passing=False,
                                                   retcode=255))
  )

  # TODO(dpranke): crbug.com/357866 . This tests what happens if we exceed the
  # number of failures specified with --exit-after-n-crashes-or-times or
  # --exit-after-n-failures; the step should be considered a hard failure and
  # we shouldn't try to compare the lists of failing tests.
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run-webkit-tests.
  yield (
    api.test('webkit_tests_interrupted') +
    properties('tryserver.blink', 'linux_blink_rel') +
    api.override_step_data(with_patch, canned_test(passing=False,
                                                   retcode=130))
  )

  yield (
    api.test('compile_failure_bot_update') +
    api.platform('linux', 64) +
    properties('tryserver.blink', 'linux_blink_bot_update') +
    api.step_data('compile', retcode=1) +
    api.step_data(with_patch, canned_test(passing=True, minimal=True))
  )

  yield (
    api.test('compile_failure_win') +
    api.platform('win', 32) +
    properties('tryserver.blink', 'win_blink_rel') +
    api.step_data('compile', retcode=1) +
    api.step_data(with_patch, canned_test(passing=True, minimal=True))
  )

  # This tests what happens if we don't trip the thresholds listed
  # above, but fail more tests than we can safely fit in a return code.
  # (this should be a soft failure and we can still retry w/o the patch
  # and compare the lists of failing tests).
  yield (
    api.test('too_many_failures_for_retcode') +
    properties('tryserver.blink', 'linux_blink_rel') +
    api.override_step_data(with_patch,
                           canned_test(passing=False,
                                       num_additional_failures=125)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )
