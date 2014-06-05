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

DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

class WebRTCNormalTests(object):
  @staticmethod
  def run(api):
    steps = []
    for test in api.webrtc.NORMAL_TESTS:
      steps.append(api.chromium.runtest(test, annotate='gtest', xvfb=True,
                                        test_type=test))

    if api.platform.is_mac and api.chromium.c.TARGET_BITS == 64:
      test = api.path.join('libjingle_peerconnection_objc_test.app', 'Contents',
                           'MacOS', 'libjingle_peerconnection_objc_test')
      steps.append(api.chromium.runtest(
          test, name='libjingle_peerconnection_objc_test', annotate='gtest',
          xvfb=True, test_type=test))
    return steps


class WebRTCBaremetalTests(object):
  def __init__(self, measure_perf=False):
    self._measure_perf = measure_perf

  def run(self, api):
    """Adds baremetal tests, which are different depending on the platform."""

    steps = []

    def add_test(test, name=None, args=None, env=None):
      args = args or []
      env = env or {}

      if self._measure_perf:
        assert api.properties.get('revision'), 'Revision must be specified.'
        steps.append(api.chromium.runtest(
            test=test, args=args, name=name, results_url=DASHBOARD_UPLOAD_URL,
            annotate='graphing', xvfb=True, perf_dashboard_id=test,
            test_type=test, env=env, revision=api.properties['revision']))
      else:
        steps.append(api.chromium.runtest(
            test=test, args=args, name=name, annotate='gtest', xvfb=True,
            test_type=test, env=env))

    if api.platform.is_win or api.platform.is_mac:
      add_test('audio_device_tests')
    elif api.platform.is_linux:
      f = api.path['checkout'].join
      add_test('audioproc', name='audioproc_perf',
               args=['-aecm', '-ns', '-agc', '--fixed_digital', '--perf', '-pb',
                     f('resources', 'audioproc.aecdump')])
      add_test('iSACFixtest', name='isac_fixed_perf',
               args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                     'isac_speech_and_misc_wb.pcm'])
      steps.append(api.webrtc.virtual_webcam_check())
      add_test('libjingle_peerconnection_java_unittest',
               env={'LD_PRELOAD': '/usr/lib/x86_64-linux-gnu/libpulse.so.0'})

    steps.append(api.webrtc.virtual_webcam_check())
    add_test('vie_auto_test',
        args=['--automated',
              '--capture_test_ensure_resolution_alignment_in_capture_device='
              'false'])
    add_test('voe_auto_test', args=['--automated'])
    steps.append(api.webrtc.virtual_webcam_check())
    add_test('video_capture_tests')
    add_test('webrtc_perf_tests')
    return steps


BUILDERS = {
  # TODO(kjellander): Deal with the massive code duplication below.
  'client.webrtc': {
    'builders': {
      'Win32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win32 Release [large tests]': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(measure_perf=True),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win Dr Memory Full': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_full'],
        'gclient_apply_config': ['drmemory'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Win Dr Memory Light': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_light'],
        'gclient_apply_config': ['drmemory'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'Mac32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac Asan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['asan'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac32 Release [large tests]': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(measure_perf=True),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'iOS Debug': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'iOS Release': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'Linux32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Memcheck': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux TSan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['tsan'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux TSan v2': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['tsan2'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Release [large tests]': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(measure_perf=True),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'Android': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android (dbg)': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Clang (dbg)': {
        'recipe_config': 'webrtc_android_clang',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'client.webrtc.fyi': {
    'builders': {
      'Linux TsanRV': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['tsan_race_verifier'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'win': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_x64_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_baremetal': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'win_drmemory_light': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_light'],
        'gclient_apply_config': ['drmemory'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'win',
        },
      },
      'mac': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_x64_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_asan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['asan'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_baremetal': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'mac',
        },
      },
      'ios': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'ios_rel': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'linux': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_memcheck': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_tsan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['tsan'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_tsan2': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['tsan2'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCNormalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_baremetal': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          WebRTCBaremetalTests(),
        ],
        'testing': {
          'platform': 'linux',
        },
      },
      'android': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'android_rel': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'android_clang': {
        'recipe_config': 'webrtc_android_clang',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}

RECIPE_CONFIGS = {
  'webrtc': {
    'webrtc_config': 'webrtc',
  },
  'webrtc_clang': {
    'webrtc_config': 'webrtc_clang',
  },
  'webrtc_android': {
    'webrtc_config': 'webrtc_android',
  },
  'webrtc_android_clang': {
    'webrtc_config': 'webrtc_android_clang',
  },
  'webrtc_ios': {
    'webrtc_config': 'webrtc_ios',
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.webrtc.set_config(recipe_config['webrtc_config'],
                        **bot_config.get('webrtc_config_kwargs', {}))
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  # Needed for the multiple webcam check steps to get unique names.
  api.step.auto_resolve_conflicts = True

  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')

  yield api.gclient.checkout()
  steps = []
  if api.tryserver.is_tryserver:
    steps.append(api.webrtc.apply_svn_patch())

  steps.append(api.chromium.runhooks())
  steps.append(api.chromium.compile())
  steps.extend([t.run(api) for t in bot_config.get('tests', [])])
  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


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
                       slavename='slavename',
                       revision='12345') +
        api.platform(bot_config['testing']['platform'],
                     webrtc_config_kwargs.get('TARGET_BITS', 64))
      )

      if mastername.startswith('tryserver'):
        test += api.properties(patch_url='try_job_svn_patch')

      if buildername.endswith('[large tests]'):
        test += api.properties(perf_id=_sanitize_nonalpha(buildername),
                               perf_config={'a_default_rev': 'r_webrtc_rev'},
                               show_perf_results=True)

      yield test
