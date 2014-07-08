# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'android',
  'path',
  'properties',
  'tryserver',
]

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
  droid = api.android
  droid.set_config('AOSP_webview')

  # Not all third party dependencies have licenses compatible with the Android
  # license. To prevent developers adding dependencies from the WebView to
  # incompatibly licensed third parties we check out a subset of DEPS.
  # The whitelist is in the android_webview/buildbot/deps_whitelist.py file.
  # This does not cover code checked into the main Chromium repository directly
  # for that we have the incompatible_directories_check_step below.
  yield droid.chromium_with_trimmed_deps()
  yield droid.lastchange_steps()

  yield api.tryserver.maybe_apply_issue()

  # Check out the Android source.
  yield droid.repo_init_steps()
  yield droid.repo_sync_steps()

  # The Android build system requires the Chromium sources be in the Android
  # tree. Luckily it doesn't mind if the tree is symlinked in.
  yield droid.symlink_chromium_into_android_tree_step()
  # This generates the Android.mk files needed by the Android build system to
  # build the parts of Chromium that are needed by the WebView.
  yield droid.gyp_webview_step()

  # This check is in place to detect incompatibly-licensed new code that's
  # checked into the main Chromium repository.
  yield droid.incompatible_directories_check_step()

  # TODO(android): use api.chromium.compile for this
  yield droid.compile_step(
    build_tool='make-android',
    targets=['webviewchromium'],
    use_goma=True)

def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()

  yield (
    api.test('uses_android_repo') +
    api.properties.scheduled() +
    api.path.exists(
      api.path['slave_build'].join('android-src', '.repo', 'repo', 'repo'))
  )

  yield (
    api.test('doesnt_sync_if_android_present') +
    api.properties.scheduled() +
    api.path.exists(api.path['slave_build'].join('android-src'))
  )

  yield (
    api.test('does_delete_stale_chromium') +
    api.properties.scheduled() +
    api.path.exists(
      api.path['slave_build'].join('android-src', 'external', 'chromium_org'))
  )

  yield (
    api.test('uses_goma_test') +
    api.properties.scheduled() +
    api.path.exists(api.path['build'].join('goma'))
  )

  yield api.test('works_if_revision_not_present') + api.properties.generic()

  yield api.test('trybot') + api.properties.tryserver()
