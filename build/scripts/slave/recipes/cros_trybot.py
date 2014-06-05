# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromite',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'rietveld',
  'step',
  'step_history',
  'tryserver',
]


# Make it easy to change how different configurations of this recipe
# work without making buildbot-side changes. Each builder will only
# have a tag specifying a config/flavor (adding, removing or changing
# builders requires a buildbot-side change anyway), but we can change
# everything about what that config means in the recipe.
RECIPE_CONFIGS = {
  # Default config.
  None: {
    'cbuildbot_config': 'x86-generic-telem-chrome-pfq-informational',
  },
  'amd64': {
    'cbuildbot_config': 'amd64-generic-telem-chrome-pfq-informational',
  },
  'x86': {
    'cbuildbot_config': 'x86-generic-telem-chrome-pfq-informational',
  },
}


CROS_BUILD = '/b/cbuild/external_master'

def GenSteps(api):
  recipe_config_name = api.properties.get('recipe_config')
  if recipe_config_name not in RECIPE_CONFIGS:
    recipe_config = {'cbuildbot_config': recipe_config_name}
  else:
    recipe_config = RECIPE_CONFIGS[recipe_config_name]

  cbuildbot_config = recipe_config['cbuildbot_config']
  cbuildbot_flags = {
      'debug': None,  # Be a try - don't write global state.
      'buildbot': None,  #  Be a bot - don't get chatty or deferrent.
      # Use the value below for uniquefying things when necessary.
      'buildnumber' : api.properties.get('buildnumber', 0),
      'buildroot': CROS_BUILD, # Use this repo-place.
      'chrome_root': '.',  # This is where we have put "Chrome".
      }
  cbuildbot_flags_clobber = cbuildbot_flags.copy()
  cbuildbot_flags_clobber.update({'clobber': None})

  chromite_path = api.path['root'].join('build', 'third_party',
                                        'cbuildbot_chromite')
  api.chromium.set_config('chromium')
  api.chromium.apply_config('trybot_flavor')
  api.gclient.set_config('chromium')
  api.step.auto_resolve_conflicts = True

  yield api.gclient.checkout(
      revert=True, can_fail_build=False, abort_on_failure=False)
  for step in api.step_history.values():
    if step.retcode != 0:
      yield (
        api.path.rmcontents('slave build directory', api.path['slave_build']),
        api.gclient.checkout(revert=False),
      )
      break

  # Note: Bug(317809) lurks around here.
  yield api.tryserver.maybe_apply_issue()

  yield api.chromite.cbuildbot(
      name='cbuildbot (with patch)',
      config=cbuildbot_config,
      flags=cbuildbot_flags,
      chromite_path=chromite_path,
      abort_on_failure=False,
      can_fail_build=False)
  if api.step_history['cbuildbot (with patch)'].retcode != 0:
    # Only use LKCR when cbuildbot fails. Note that requested specific revision
    # can still override this.
    api.gclient.set_config('chromium_lkcr')

    # Since we're likely to switch to an earlier revision, revert the patch,
    # sync with the new config, and apply issue again.
    yield api.gclient.checkout(revert=True)
    yield api.rietveld.apply_issue()

    yield api.chromite.cbuildbot(
        name='cbuildbot (with patch, lkcr, clobber)',
        config=cbuildbot_config,
        flags=cbuildbot_flags_clobber,
        chromite_path=chromite_path,
        abort_on_failure=False,
        can_fail_build=False)
    if api.step_history['cbuildbot (with patch, lkcr, clobber)'].retcode != 0:
      yield (
        api.path.rmcontents('slave build directory', api.path['slave_build']),
        api.gclient.checkout(revert=False),
        api.rietveld.apply_issue(),
        api.chromite.cbuildbot(
            name='cbuildbot (with patch, lkcr, clobber, nuke)',
            config=cbuildbot_config,
            flags=cbuildbot_flags_clobber,
            chromite_path=chromite_path)
        )


def GenTests(api):
  def props(config='Release', **kwargs):
    kwargs.setdefault('revision', None)
    return api.properties.tryserver(
      build_config=config,
      **kwargs
    ) + api.platform.name('linux')


  # While not strictly required for coverage, record expectations for each
  # of the configs so we can see when and how they change.
  for config in RECIPE_CONFIGS:
    if config:
      yield (
        api.test(config) +
        props(recipe_config=config)
      )

  yield (
    api.test('cr48-firmware') +
    props(recipe_config='cr48-firmware')
  )

  for step in ('gclient revert', 'gclient runhooks'):
    yield (
      api.test(step.replace(' ', '_') + '_failure') +
      props()
    )

  yield (
    api.test('gclient_revert_failure_linux') +
    props()
  )

  yield (
    api.test('gclient_sync_no_data') +
    props() +
    api.platform.name('linux') +
    api.override_step_data('gclient sync', api.json.output(None))
  )

  yield (
    api.test('gclient_revert_nuke') +
    props() +
    api.step_data('gclient revert', retcode=1)
  )

  yield (
    api.test('cbuildbot_failure') +
    props() +
    api.step_data('cbuildbot (with patch)', retcode=1) +
    api.step_data('cbuildbot (with patch, lkcr, clobber)', retcode=1) +
    api.step_data('cbuildbot (with patch, lkcr, clobber, nuke)', retcode=1)
  )
