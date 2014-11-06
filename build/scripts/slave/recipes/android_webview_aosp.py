# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'android',
  'chromium_android',
  'filter',
  'json',
  'path',
  'properties',
  'raw_io',
  'tryserver',
]

AOSP_MANIFEST_PATH = 'android_webview/buildbot/aosp_manifest.xml'
WEBVIEW_EXES = ['android_webview_apk']

# This recipe describes building the Android framework WebView component inside
# an Android build environment.
# The developer instructions for building Android are available on the wiki:
# http://www.chromium.org/developers/how-tos/build-instructions-android-webview
#
# In order to build a fully functional Android WebView it is necessary to
# compile against parts of the Android system that are not part of the Android
# SDK that the 'regular' Chromium build uses. This is why the recipe requires
# checking out the Android source tree and building using the Android build
# system.

def GenSteps(api):
  # Required for us to be able to use filter.
  api.chromium_android.set_config('base_config')

  droid = api.android
  droid.set_config('AOSP_webview')

  # Not all third party dependencies have licenses compatible with the Android
  # license. To prevent developers adding dependencies from the WebView to
  # incompatibly licensed third parties we build with only the known
  # compatible subset of the source.
  # We start with the main Chromium repository and none of the deps.
  # Compatible deps are added based on a whitelist of deps is in the
  # android_webview/buildbot/deps_whitelist.py file. Incompatible code
  # checked directly into Chromium is removed based on a blacklist in
  # webview/tools/known_issues.py.
  # After we have put the right parts of the source into the Android checkout
  # we use the all_incompatible_directories_check_step to check nothing is
  # incompatible licenced.

  spec = droid.create_spec()
  droid.sync_chromium(spec)

  droid.lastchange_steps()

  api.tryserver.maybe_apply_issue()

  # Check out the Android source.
  droid.repo_init_steps()
  droid.repo_sync_steps()

  # The Android build system requires the Chromium sources be in the Android
  # tree. We rsync everything accept the blacklisted source into the Android
  # tree.
  droid.rsync_chromium_into_android_tree_step()

  # This generates the Android.mk files needed by the Android build system to
  # build the parts of Chromium that are needed by the WebView.
  droid.gyp_webview_step()

  # This check is in place to detect incompatibly-licensed new code that's
  # checked into the main Chromium repository.
  droid.all_incompatible_directories_check_step()

  # Early out if we haven't changed any relevant code.
  api.filter.does_patch_require_compile(exes=WEBVIEW_EXES,
                                        additional_name='android_webview')
  needs_compile = not api.filter.result or not api.filter.matching_exes
  if api.tryserver.is_tryserver and needs_compile:
    return

  # If the Manifest has changed then we need to recompile everything.
  force_clobber = AOSP_MANIFEST_PATH in api.filter.paths

  # TODO(android): use api.chromium.compile for this
  droid.compile_step(
    build_tool='make-android',
    targets=['webviewchromium'],
    use_goma=True,
    force_clobber=force_clobber)

def GenTests(api):
  analyze_config = api.override_step_data(
      'read filter exclusion spec',
      api.json.output({
        'base': {
          'exclusions': [],
        },
        'android_webview': {
          'exclusions': ['android_webview/.*'],
        },
      })
  )

  chrome_change = analyze_config + api.override_step_data(
      'git diff to analyze patch',
      api.raw_io.stream_output('chrome/common/my_file.cc'))

  manifest_change = analyze_config + api.override_step_data(
      'git diff to analyze patch',
      api.raw_io.stream_output(AOSP_MANIFEST_PATH))

  dependant_change = analyze_config + api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'targets': ['android_webview_apk'],
                       'build_targets': ['some_target']}))

  yield api.test('basic') + api.properties.scheduled() + dependant_change

  yield (
    api.test('repo_infra_failure') +
    api.properties.scheduled() +
    api.step_data('repo sync', retcode=1)
  )

  yield (
    api.test('uses_android_repo') +
    api.properties.scheduled() +
    api.path.exists(
      api.path['slave_build'].join('android-src', '.repo', 'repo', 'repo')) +
    dependant_change
  )

  yield (
    api.test('can_clobber') +
    api.properties.scheduled(clobber=True) +
    dependant_change
  )

  yield (
    api.test('manifest_changes_cause_clobber') +
    api.properties.scheduled() +
    manifest_change
  )

  yield (
    api.test('uses_goma_test') +
    api.properties.scheduled() +
    dependant_change +
    api.path.exists(api.path['build'].join('goma'))
  )

  yield (
    api.test('works_if_revision_not_present') +
    api.properties.generic() +
    dependant_change
  )

  yield (
    api.test('trybot') +
    api.properties.tryserver() +
    dependant_change
  )

  yield (
    api.test('build_compiles_chrome_only_changes') +
    api.properties.scheduled() +
    chrome_change
  )

  yield (
    api.test('trybot_doesnt_compile_chrome_only_changes') +
    api.properties.tryserver() +
    chrome_change
  )
