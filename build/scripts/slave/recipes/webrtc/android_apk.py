# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'base_android',
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

# Map of GS archive names to urls.
GS_ARCHIVES = {
  'android_dbg_archive': 'gs://chromium-webrtc/android_dbg',
  'android_rel_archive': 'gs://chromium-webrtc/android_rel',
}

BUILDERS = {
  'client.webrtc': {
    'builders': {
      # Builders.
      'Android Chromium-APK Builder (dbg)': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'Android Chromium-APK Builder': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_rel_archive',
        'testing': {'platform': 'linux'},
      },
      # Testers.
      'Android Chromium-APK Tests (KK Nexus5)(dbg)': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Chromium-APK Builder (dbg)',
        'build_gs_archive': 'android_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'Android Chromium-APK Tests (KK Nexus5)': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Chromium-APK Builder',
        'build_gs_archive': 'android_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'Android Chromium-APK Tests (JB Nexus7.2)(dbg)': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Chromium-APK Builder (dbg)',
        'build_gs_archive': 'android_dbg_archive',
        'testing': {'platform': 'linux'},
      },
      'Android Chromium-APK Tests (JB Nexus7.2)': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Chromium-APK Builder',
        'build_gs_archive': 'android_rel_archive',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'android_apk': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_apk_rel': {
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
    },
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name %r for master %r.' %
                      (buildername, mastername))

  # The infrastructure team has recommended not to use git yet on the
  # bots, but it's very nice to have when testing locally.
  # To use, pass "use_git=True" as an argument to run_recipe.py.
  use_git = api.properties.get('use_git', False)

  api.webrtc.set_config('webrtc_android_apk',
                        GIT_MODE=use_git,
                        **bot_config.get('webrtc_config_kwargs', {}))
  if api.tryserver.is_tryserver:
    api.webrtc.apply_config('webrtc_android_apk_try_builder')

  revision = api.properties.get('revision')
  assert revision, 'WebRTC revision must be specified as "revision" property"'

  # Replace src/third_party/webrtc with the specified revision and force the
  # Chromium code to sync ToT.
  s = api.gclient.c.solutions
  s[0].revision = 'HEAD'
  s[0].custom_vars['webrtc_revision'] = revision
  yield api.gclient.checkout()

  bot_type = bot_config.get('bot_type', 'builder_tester')
  if bot_type in ['builder', 'builder_tester']:
    if api.tryserver.is_tryserver:
      yield api.webrtc.apply_svn_patch()
    yield api.base_android.envsetup()

  # WebRTC Android APK testers also have to run the runhooks, since test
  # resources are currently downloaded during this step.
  yield api.base_android.runhooks()

  yield api.chromium.cleanup_temp()
  if bot_type in ['builder', 'builder_tester']:
    yield api.base_android.compile()

  if bot_type == 'builder':
    yield(api.archive.zip_and_upload_build(
          'package build',
          api.chromium.c.build_config_fs,
          GS_ARCHIVES[bot_config['build_gs_archive']],
          build_revision=revision))

  if bot_type == 'tester':
    yield(api.archive.download_and_unzip_build(
          'extract build',
          api.chromium.c.build_config_fs,
          GS_ARCHIVES[bot_config['build_gs_archive']],
          build_revision=revision,
          abort_on_failure=True))

  if bot_type in ['tester', 'builder_tester']:
    yield api.chromium_android.common_tests_setup_steps()
    for test in api.webrtc.ANDROID_APK_TESTS:
      yield api.base_android.test_runner(test)

    yield api.chromium_android.common_tests_final_steps()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config.get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      webrtc_config_kwargs = bot_config.get('webrtc_config_kwargs', {})
      test = (
        api.test('%s_%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername))) +
        api.properties(mastername=mastername,
                       buildername=buildername,
                       parent_buildername=bot_config.get('parent_buildername'),
                       TARGET_PLATFORM=webrtc_config_kwargs['TARGET_PLATFORM'],
                       TARGET_ARCH=webrtc_config_kwargs['TARGET_ARCH'],
                       TARGET_BITS=webrtc_config_kwargs['TARGET_BITS'],
                       BUILD_CONFIG=webrtc_config_kwargs['BUILD_CONFIG'],
                       revision='12345') +
        api.platform(bot_config['testing']['platform'],
                     webrtc_config_kwargs.get('TARGET_BITS', 64))
      )
      if bot_type in ['builder', 'builder_tester']:
        test += api.step_data('envsetup',
            api.json.output({
                'FOO': 'bar',
                'GYP_DEFINES': 'my_new_gyp_def=aaa',
             }))

      if bot_type == 'tester':
        test += api.properties(parent_got_revision='12345')

      if mastername.startswith('tryserver'):
        test += api.properties(patch_url='try_job_svn_patch')

      yield test

