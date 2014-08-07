# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'gsutil',
  'properties',
  'json',
  'path',
  'python',
]

BUILDERS = {
  'local_test': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src.git',
      'REPO_NAME': 'src',
    },
    'custom': {
      'deps_file': '.DEPS.git'
    },
    'gyp_defs': {
      'use_goma': 0,
    }
  },
  'Android Cronet Builder (dbg)': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
  'Android Cronet Builder': {
    'recipe_config': 'main_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
  'Android Cronet ARMv6 Builder': {
    'recipe_config': 'main_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
    'gyp_defs': {
      'arm_version': 6
    }
  },
  'Android Cronet x86 Builder': {
    'recipe_config': 'x86_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
  'Android Cronet MIPS Builder': {
    'recipe_config': 'mipsel_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
}

def GenSteps(api):
  droid = api.chromium_android

  buildername = api.properties['buildername']
  builder_config = BUILDERS.get(buildername, {})
  default_kwargs = {
    'REPO_URL': '/'.join((api.properties.get('repository') or '',
                          api.properties.get('branch') or '')),
    'INTERNAL': False,
    'REPO_NAME': api.properties.get('branch') or '',
    'BUILD_CONFIG': 'Debug'
  }

  kwargs = builder_config.get('kwargs', {})
  droid.configure_from_properties(builder_config['recipe_config'],
      **dict(default_kwargs.items() + kwargs.items()))
  droid.c.set_val(builder_config.get('custom', {}))

  api.chromium.apply_config('cronet_builder')
  gyp_defs = api.chromium.c.gyp_env.GYP_DEFINES
  gyp_defs.update(builder_config.get('gyp_defs', {}))

  yield droid.init_and_sync()
  yield droid.clean_local_files()
  yield droid.runhooks()
  yield droid.compile()

  revision = api.properties.get('revision')
  cronetdir = api.path['checkout'].join('out', droid.c.BUILD_CONFIG, 'cronet')
  if builder_config['upload_package']:
    destdir = 'cronet-%s-%s' % (kwargs['BUILD_CONFIG'], revision)
    yield api.gsutil.upload(
        source=cronetdir,
        bucket='chromium-cronet/android',
        dest=destdir,
        args=['-R'],
        name='upload_cronet_package',
        link_name='Cronet package')

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

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())

def GenTests(api):
  bot_ids = ['local_test', 'Android Cronet Builder (dbg)',
      'Android Cronet Builder', 'Android Cronet ARMv6 Builder',
      'Android Cronet MIPS Builder', 'Android Cronet x86 Builder']

  for bot_id in bot_ids:
    props = api.properties.generic(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      repository='svn://svn-mirror.golo.chromium.org/chrome/trunk',
      branch='src',
    )
    yield api.test(_sanitize_nonalpha(bot_id)) + props
