# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')
def linux_android(): return chromium_factory.ChromiumFactory(
    'src/build', 'linux2', nohooks_on_update=True, target_os='android')

defaults['category'] = '1clobber'

# Global scheduler
S('chromium', branch='src', treeStableTimer=60)

################################################################################
## Windows
################################################################################

B('Win', 'win_clobber', 'compile|windows', 'chromium',
  notify_on_missing=True)
F('win_clobber', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    tests=[
      'check_bins',
      'check_deps2git',
      'sizes',
    ],
    factory_properties={
      'archive_build': True,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-xp',
      'expectations': True,
      'process_dumps': True,
      'start_crash_handler': True,
      'generate_gtest_json': True,
      'gclient_env': {
        'GYP_DEFINES': 'test_isolation_mode=noop',
      },
    }))

################################################################################
## Mac
################################################################################

B('Mac', 'mac_clobber', 'compile|testers', 'chromium',
  notify_on_missing=True)
F('mac_clobber', mac().ChromiumFactory(
    clobber=True,
    tests=[
      'check_deps2git',
      'sizes',
    ],
    options=['--compiler=goma-clang'],
    factory_properties={
      'archive_build': True,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-mac',
      'expectations': True,
      'generate_gtest_json': True,
      'gclient_env': {
        'GYP_DEFINES': 'test_isolation_mode=noop',
      },
    }))

################################################################################
## Linux
################################################################################

B('Linux', 'linux_clobber', 'compile|testers', 'chromium',
  notify_on_missing=True)
F('linux_clobber', linux().ChromiumFactory(
    clobber=True,
    tests=[
      'check_deps2git',
      'check_licenses',
      'check_perms',
      'sizes',
    ],
    options=['--compiler=goma'],
    factory_properties={
      'archive_build': True,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-linux',
      'expectations': True,
      'generate_gtest_json': True,
      'gclient_env': {
        'GYP_DEFINES': 'target_arch=ia32 test_isolation_mode=noop',
      },
    }))

B('Linux x64', 'linux64_clobber', 'compile|testers', 'chromium',
  notify_on_missing=True)
F('linux64_clobber', linux().ChromiumFactory(
    clobber=True,
    tests=[
      'check_deps2git',
      'sizes',
    ],
    options=['--compiler=goma', '--build-tool=ninja', 'all'],
    factory_properties={
      'archive_build': True,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'generate_gtest_json': True,
      'perf_id': 'chromium-rel-linux-64',
      'expectations': True,
      'gclient_env': {
        'GYP_DEFINES': 'target_arch=x64 test_isolation_mode=noop',
        'GYP_GENERATORS': 'ninja',
      },
    }))

################################################################################
## Android
################################################################################

B('Android', 'f_android_clobber', None, 'chromium',
  notify_on_missing=True)
F('f_android_clobber', linux_android().ChromiumAnnotationFactory(
    clobber=True,
    target='Release',
    tests=[
      'sizes',
    ],
    factory_properties={
      'show_perf_results': True,
      'perf_id': 'android-release',
    },
    annotation_script='src/build/android/buildbot/bb_main_clobber.sh',
    ))


def Update(config, active_master, c):
  return helper.Update(c)
