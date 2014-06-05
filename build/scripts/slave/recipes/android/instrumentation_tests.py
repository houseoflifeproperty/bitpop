# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_android',
  'generator_script',
  'properties',
  'json',
]

def GenSteps(api):
  droid = api.chromium_android
  bot_id = api.properties['android_bot_id']
  droid.configure_from_properties(bot_id)
  yield droid.common_tree_setup_steps()
  if bot_id in ['try_instrumentation_tests', 'x86_try_instrumentation_tests']:
    yield droid.apply_svn_patch()
  yield droid.download_build()
  yield droid.common_tests_setup_steps()
  yield droid.instrumentation_tests()
  yield droid.common_tests_final_steps()

def GenTests(api):
  bot_ids = ['main_tests', 'clang_tests', 'enormous_tests',
             'try_instrumentation_tests', 'x86_try_instrumentation_tests']

  def common_test_data(props, include_tests=True):
    test_data = (
        props +
        api.chromium_android.default_step_data(api)
    )
    if include_tests:
      # TODO(sivachandra): Move this generator script's test to
      # chromium_android/test_api.py
      test_data += api.generator_script(
          'tests_generator.py',
          {'name': 'test_step', 'cmd': ['path/to/test_script.py']}
      )
    return test_data

  def props(bot_id):
    return api.properties(
      repo_name='src/repo',
      repo_url='svn://svn.chromium.org/chrome/trunk/src',
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      android_bot_id=bot_id,
      buildername='test_buildername',
      parent_buildername='parent_buildername',
      parent_buildnumber='1729',
      internal=True
    )

  for bot_id in bot_ids:
    p = props(bot_id)
    if 'try_instrumentation_tests' in bot_id:
      p += api.properties(revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00')
      p += api.properties(parent_buildnumber=1357)
      p += api.properties(patch_url='try_job_svn_patch')

    yield api.test(bot_id) + common_test_data(p)

  # failure tests
  yield (api.test('main_tests_device_status_check_fail') +
         common_test_data(props('main_tests'), include_tests=False) +
         api.step_data('device_status_check', retcode=1))
  yield (api.test('main_tests_deploy_fail') +
         common_test_data(props('main_tests'), include_tests=False) +
         api.step_data('deploy_on_devices', retcode=1))
  yield (api.test('main_tests_provision_fail') +
         common_test_data(props('main_tests')) +
         api.step_data('provision_devices', retcode=1))
