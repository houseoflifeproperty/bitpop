# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from slave import recipe_api

DEPS = [
  'chromium_android',
  'bot_update',
  'gclient',
  'path',
  'properties',
  'step',
  'tryserver',
]

# Step types
@contextmanager
def NormalStep():
  yield

@contextmanager
def FYIStep():
  try:
    yield
  except recipe_api.StepFailure:
    pass

BUILDERS = {
  'chromium.fyi': {
    'Android x64 Builder (dbg)': {
      'recipe_config': 'x64_builder',
      'check_licenses': FYIStep,
      'findbugs': FYIStep,
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
    'Android MIPS Builder (dbg)': {
      'recipe_config': 'mipsel_builder',
      'check_licenses': FYIStep,
      'findbugs': FYIStep,
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
    'Android Builder (dbg)': {
      'recipe_config': 'main_builder',
      'check_licenses': NormalStep,
      'findbugs': NormalStep,
      'upload': {
        'bucket': 'chromium_android',
        'path': lambda api: ('android_fyi_dbg/full-build-linux_%s.zip' %
                             api.properties['revision']),
      },
    },
    'Android Builder': {
      'recipe_config': 'main_builder',
      'check_licenses': NormalStep,
      'findbugs': NormalStep,
      'upload': {
        'bucket': 'chromium_android',
        'path': lambda api: ('android_fyi_rel/full-build-linux_%s.zip' %
                             api.properties['revision']),
      },
      'target': 'Release',
    },
    'Android Clang Builder (dbg)': {
      'recipe_config': 'clang_builder',
    },
  },
  'chromium.linux': {
    'Android Arm64 Builder (dbg)': {
      'recipe_config': 'arm64_builder',
      'check_licenses': FYIStep,
      'findbugs': FYIStep,
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
  },
  'tryserver.chromium.linux': {
    'android_clang_dbg_recipe': {
      'recipe_config': 'clang_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'try': True,
      'check_licenses': NormalStep,
      'findbugs': NormalStep,
    },
    'android_arm64_dbg_recipe': {
      'recipe_config': 'arm64_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'try': True,
      'check_licenses': FYIStep,
      'findbugs': FYIStep,
    },
    'android_x86_dbg_recipe': {
      'recipe_config': 'x86_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'try': True,
      'findbugs': FYIStep,
    },
    'blink_android_compile_dbg_recipe': {
      'recipe_config': 'main_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'try': True,
    },
    'blink_android_compile_rel_recipe': {
      'recipe_config': 'main_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'try': True,
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
    },
  },
  'chromium.perf.fyi': {
    'android_oilpan_builder': {
      'recipe_config': 'oilpan_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'chromium-android',
        'path': lambda api: (
          '%s/build_product_%s.zip' % (api.properties['buildername'],
                                       api.properties['revision'])),
      }
    },
  },
  'chromium.perf': {
    'Android Builder': {
      'recipe_config': 'perf',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'chrome-perf',
        'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                             % api.properties['revision']),
      }
    }
  },
  'client.v8': {
    'Android Builder': {
      'recipe_config': 'perf',
      'gclient_apply_config': [
        'android',
        'perf',
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'v8-android',
        'path': lambda api: ('v8_android_perf_rel/full-build-linux_%s.zip'
                             % api.properties['revision']),
      },
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
    }
  },
}

def GenSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config = BUILDERS[mastername][buildername]
  droid = api.chromium_android

  default_kwargs = {
    'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
    'INTERNAL': False,
    'REPO_NAME': 'src',
    'BUILD_CONFIG': bot_config.get('target', 'Debug'),
  }
  default_kwargs.update(bot_config.get('kwargs', {}))
  droid.configure_from_properties(bot_config['recipe_config'], **default_kwargs)
  droid.c.set_val({'deps_file': 'DEPS'})

  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if bot_config.get('set_component_rev'):
    # If this is a component build and the main revision is e.g. blink,
    # webrtc, or v8, the custom deps revision of this component must be
    # dynamically set to either:
    # (1) 'revision' from the waterfall, or
    # (2) 'HEAD' for forced builds with unspecified 'revision'.
    component_rev = api.properties.get('revision', 'HEAD')
    dep = bot_config.get('set_component_rev')
    api.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

  bot_update_step = api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()

  droid.runhooks()

  if bot_config.get('try', False):
    api.tryserver.maybe_apply_issue()

    try:
      droid.compile(name='compile (with patch)')
    except api.step.StepFailure:
      bot_update_json = bot_update_step.json.output
      api.gclient.c.revisions['src'] = str(
          bot_update_json['properties']['got_revision'])
      api.bot_update.ensure_checkout(force=True,
                                     patch=False,
                                     update_presentation=False)
      try:
        droid.runhooks()
        droid.compile(name='compile (without patch)')

        # TODO(phajdan.jr): Set failed tryjob result after recognizing infra
        # compile failures. We've seen cases of compile with patch failing
        # with build steps getting killed, compile without patch succeeding,
        # and compile with patch succeeding on another attempt with same patch.
      except api.step.StepFailure:
        api.tryserver.set_transient_failure_tryjob_result()
        raise
      raise
  else:
    droid.compile()

  if bot_config.get('check_licenses'):
    with bot_config['check_licenses']():
      droid.check_webview_licenses()
  if bot_config.get('findbugs'):
    with bot_config['findbugs']():
      droid.findbugs()

  upload_config = bot_config.get('upload')
  if upload_config:
    droid.upload_build(upload_config['bucket'],
                       upload_config['path'](api))


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  # tests bots in BUILDERS
  for mastername, builders in BUILDERS.iteritems():
    for buildername in builders:
      yield (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(buildername=buildername,
            repository='svn://svn.chromium.org/chrome/trunk/src',
            buildnumber=257,
            mastername=mastername,
            issue='8675309',
            patchset='1',
            revision='267739',
            got_revision='267739'))

  def step_failure(mastername, buildername, steps, tryserver=False):
    props = api.properties.tryserver if tryserver else api.properties.generic
    return (
      api.test('%s_%s_fail_%s' % (
        _sanitize_nonalpha(mastername),
        _sanitize_nonalpha(buildername),
        '_'.join(_sanitize_nonalpha(step) for step in steps))) +
      props(mastername=mastername, buildername=buildername) +
      reduce(lambda a, b: a + b,
             (api.step_data(step, retcode=1) for step in steps))
    )

  yield step_failure(mastername='chromium.fyi',
                     buildername='Android x64 Builder (dbg)',
                     steps=['findbugs'])
  yield step_failure(mastername='chromium.fyi',
                     buildername='Android x64 Builder (dbg)',
                     steps=['check licenses'])

  yield step_failure(mastername='tryserver.chromium.linux',
                     buildername='android_clang_dbg_recipe',
                     steps=['compile (with patch)'],
                     tryserver=True)
  yield step_failure(mastername='tryserver.chromium.linux',
                     buildername='android_clang_dbg_recipe',
                     steps=['compile (with patch)', 'compile (without patch)'],
                     tryserver=True)
  yield step_failure(mastername='tryserver.chromium.linux',
                     buildername='android_clang_dbg_recipe',
                     steps=['findbugs'],
                     tryserver=True)
  yield step_failure(mastername='tryserver.chromium.linux',
                     buildername='android_clang_dbg_recipe',
                     steps=['check licenses'],
                     tryserver=True)
