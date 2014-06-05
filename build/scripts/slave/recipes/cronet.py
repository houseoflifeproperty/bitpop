# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'properties',
  'json',
  'path',
  'python',
]

BUILDERS = {
  'Android Cronet Builder (dbg)': {
    'recipe_config': 'cronet_builder',
    'run_tests': True,
  },
  'Android Cronet Builder': {
    'recipe_config': 'cronet_rel',
    'run_tests': False,
  },
}

def GenSteps(api):
  droid = api.chromium_android

  buildername = api.properties['buildername']
  builder_config = BUILDERS.get(buildername, {})
  droid.set_config(builder_config['recipe_config'],
      REPO_NAME='src',
      REPO_URL='svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
      INTERNAL=False)
  droid.c.deps_file = 'DEPS'

  yield droid.init_and_sync()
  yield droid.clean_local_files()
  yield droid.runhooks()
  yield droid.compile()
  yield droid.upload_build()

  if builder_config['run_tests']:
    yield droid.common_tests_setup_steps()
    install_cmd = api.path['checkout'].join('build',
                                            'android',
                                            'adb_install_apk.py')
    yield api.python('install CronetSample', install_cmd,
        args = ['--apk', 'CronetSample.apk'])
    test_cmd = api.path['checkout'].join('build',
                                         'android',
                                         'test_runner.py')
    yield api.python('test CronetSample', test_cmd,
        args = ['instrumentation', '--test-apk', 'CronetSampleTest'])
    yield droid.common_tests_final_steps()
  else:
    yield droid.cleanup_build()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())

def GenTests(api):
  bot_ids = ['Android Cronet Builder (dbg)', 'Android Cronet Builder']

  for bot_id in bot_ids:
    props = api.properties(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
    )
    yield api.test(_sanitize_nonalpha(bot_id)) + props
