# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'git',
    'json',
    'path',
    'perf_dashboard',
    'platform',
    'properties',
    'python',
    'raw_io',
    'step',
    'step_history'
]

# Constants
ANDROID_TOOLS_GIT = 'https://chromium.googlesource.com/android_tools'
TEST_FILES_URL = 'http://downloads.webmproject.org/test_data/libvpx'

# Device root is a special folder on the device which we have permissions to
# read / write
DEVICE_ROOT = "/data/local/tmp"

# TODO (joshualitt) the configure script is messed up so we need a relative
# path.  Essentially, it must be using argv[0] when invoking some of the
# scripts in the libvpx directory
CONFIGURE_PATH_REL = './libvpx/configure'

BUILDER_TO_DEVICE = {
  "Nexus 5 Builder" : "nexus_5",
  "Nexus 7 Builder" : "nexus_7"
}

def GenSteps(api):
  api.step.auto_resolve_conflicts = True

  # Paths and other constants
  build_root = api.path['slave_build']

  # Android tools DEPS
  android_tools_root = build_root.join('android_tools')
  adb = android_tools_root.join('sdk', 'platform-tools', 'adb')
  ndk_root = android_tools_root.join('ndk')

  # libvpx paths
  libvpx_git_url = api.properties['libvpx_git_url']
  libvpx_root = build_root.join('libvpx')
  test_data = build_root.join('test_data')

  yield api.python.inline(
      'clean_build', r"""
          import os, sys, shutil
          root = sys.argv[1]
          nuke_dirs = sys.argv[2:]
          for fname in os.listdir(root):
            path = os.path.join(root, fname)
            if os.path.isfile(path):
              os.unlink(path)
            elif fname in nuke_dirs:
              shutil.rmtree(path)
      """, args=[build_root, 'libs', 'obj', 'armeabi-v7a'])

  # Checkout android_tools and libvpx.  NDK and SDK are required to build
  # libvpx for android
  yield api.git.checkout(
      ANDROID_TOOLS_GIT, dir_path=android_tools_root, recursive=True)
  yield api.git.checkout(
      libvpx_git_url, dir_path=libvpx_root, recursive=True)

  yield api.step(
      'configure', [
          CONFIGURE_PATH_REL, '--disable-examples', '--disable-install-docs',
          '--disable-install-srcs', '--enable-unit-tests', '--enable-webm-io',
          '--disable-vp8-encoder', '--disable-vp9-encoder',
          '--enable-decode-perf-tests', '--enable-external-build',
          '--enable-vp8-decoder', '--enable-vp9-decoder',
          '--sdk-path=%s' % ndk_root, '--target=armv7-android-gcc'])

  # NDK requires NDK_PROJECT_PATH environment variable to be defined
  yield api.step(
      'ndk-build', [
          ndk_root.join('ndk-build'),
          'APP_BUILD_SCRIPT=%s'
              % libvpx_root.join('test', 'android', 'Android.mk'),
          'APP_ABI=armeabi-v7a', 'APP_PLATFORM=android-14',
          'APP_OPTIM=release', 'APP_STL=gnustl_static'],
      env={'NDK_PROJECT_PATH' : build_root}, abort_on_failure=True)

  test_root = libvpx_root.join('test')
  yield api.python(
      'get_files', test_root.join('android', 'get_files.py'),
      args=[
          '-i', test_root.join('test-data.sha1'),
          '-o', test_data, '-u', TEST_FILES_URL])

  yield api.python(
      'transfer_files',
      api.path['build'].join('scripts', 'slave', 'android',
                             'transfer_files.py'),
      args=[adb, DEVICE_ROOT, test_data])

  lib_root = build_root.join('libs', 'armeabi-v7a')
  yield api.step('push_so', [ adb, 'push', lib_root, DEVICE_ROOT])

  yield api.python.inline(
      'adb_wrap', r"""
          import sys, subprocess, time
          out = open(sys.argv[1], "w")
          p = subprocess.Popen(sys.argv[2:], stdout=out)
          while p.poll() is None:
              print "Still working"
              time.sleep(60)
          print "done"
          sys.exit(p.returncode)
      """, args=[api.raw_io.output(), adb, 'shell',
          'LD_LIBRARY_PATH=' + DEVICE_ROOT,
          'LIBVPX_TEST_DATA_PATH=' + DEVICE_ROOT, DEVICE_ROOT +
          '/vpx_test'],
          can_fail_build=True)

  yield api.python(
      'scrape_logs',
      libvpx_root.join('test', 'android', 'scrape_gtest_log.py'),
      args=['--output-json', api.json.output()],
      stdin=api.raw_io.input(api.step_history.last_step().raw_io.output))

  data = api.step_history.last_step().json.output
  # Data is json array in the format as follows:
  # videoName: name
  # threadCount: #ofthreads
  # framesPerSecond: fps
  points = []
  device = BUILDER_TO_DEVICE[api.properties["buildername"]]
  testname = "libvpx/decode/perf_test/" + device + "/"
  for i in data:
    p = api.perf_dashboard.get_skeleton_point( testname + i["videoName"] +
        "_" + str(i["threadCount"]), api.properties['buildnumber'],
        i["framesPerSecond"])
    p['units'] = "fps"
    points.append(p)

  api.perf_dashboard.set_default_config()
  yield api.perf_dashboard.post(points)

def GenTests(api):
  # Right now we just support linux, but one day we will have mac and windows
  # as well
  yield (
    api.test('basic_linux_64') +
    api.properties(
        libvpx_git_url='https://chromium.googlesource.com/webm/libvpx',
        slavename='libvpx-bot', buildername='Nexus 5 Builder',
        mastername='client.libvpx', buildnumber='75') +
    api.step_data('adb_wrap',
        api.raw_io.output("This is text with json inside normally")) +
    api.step_data('scrape_logs', api.json.output(
            [
                {
                    "decodeTimeSecs": 29.344307,
                    "framesPerSecond": 609.82868,
                    "threadCount": 1,
                    "totalFrames": 17895,
                    "version": "v1.3.0-2045-g38c2d37",
                    "videoName": "vp90-2-bbb_426x240_tile_1x1_180kbps.webm"
                },
                {
                    "decodeTimeSecs": 56.277676,
                    "framesPerSecond": 317.976883,
                    "threadCount": 2,
                    "totalFrames": 17895,
                    "version": "v1.3.0-2045-g38c2d37",
                    "videoName": "vp90-2-bbb_640x360_tile_1x2_337kbps.webm"
                 }
            ])))
