# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumGit

defaults = {}

helper = master_config.Helper(defaults)
S = helper.Scheduler
B = helper.Builder
F = helper.Factory

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def mac(): return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')
def linux(): return chromium_factory.ChromiumFactory(
    'src/out', 'linux2', pull_internal=False)

defaults['category'] = '1clobber'

# Global scheduler
S('chromium-git', branch='git-svn', treeStableTimer=60)

################################################################################
## Windows
################################################################################

B('WinGit', 'win', 'compile|testers', 'chromium-git',
  notify_on_missing=True)
F('win', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    tests=[
      'check_bins',
      'check_deps2git',
      'sizes',
    ],
    options=['--compiler=goma'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-win-git',
      'expectations': True,
      'process_dumps': True,
      'start_crash_handler': True,
      'generate_gtest_json': ActiveMaster.is_production_host,
      'gclient_env': {
        'GYP_DEFINES': 'test_isolation_mode=noop',
        'GYP_USE_SEPARATE_MSPDBSRV': '1',
      },
    }))

B('WinGit XP', 'winxp', 'compile|testers', 'chromium-git',
  notify_on_missing=True)
F('winxp', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    tests=[
      'check_bins',
      'check_deps2git',
      'sizes',
    ],
    options=['--compiler=goma'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-xp-git',
      'expectations': True,
      'process_dumps': True,
      'start_crash_handler': True,
      'generate_gtest_json': ActiveMaster.is_production_host,
      'gclient_env': {
        'GYP_DEFINES': 'test_isolation_mode=noop',
        'GYP_USE_SEPARATE_MSPDBSRV': '1',
      },
    }))

################################################################################
## Mac
################################################################################

B('MacGit', 'mac', 'compile|testers', 'chromium-git',
  notify_on_missing=True)
F('mac', mac().ChromiumFactory(
    clobber=True,
    tests=[
      'check_deps2git',
      'sizes',
    ],
    options=['--compiler=goma-clang'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-mac-git',
      'expectations': True,
      'generate_gtest_json': ActiveMaster.is_production_host,
      'gclient_env': {
        'GYP_DEFINES': 'test_isolation_mode=noop mac_strip_release=1',
      },
    }))

################################################################################
## Linux
################################################################################

B('LinuxGit', 'linux', 'compile|testers', 'chromium-git',
  notify_on_missing=True)
F('linux', linux().ChromiumFactory(
    clobber=True,
    tests=[
      'check_deps2git',
      'check_licenses',
      'check_perms',
      'sizes',
    ],
    options=['--compiler=goma', '--', 'all'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'perf_id': 'chromium-rel-linux-git',
      'expectations': True,
      'generate_gtest_json': ActiveMaster.is_production_host,
      'gclient_env': {
        'GYP_DEFINES':
            'target_arch=ia32 test_isolation_mode=noop linux_dump_symbols=0',
      },
    }))

B('LinuxGit x64', 'linux64', 'compile|testers', 'chromium-git',
  notify_on_missing=True)
F('linux64', linux().ChromiumFactory(
    clobber=True,
    tests=[
      'check_deps2git',
      'sizes',
    ],
    options=['--compiler=goma', '--', 'all'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gs_bucket': 'gs://chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'show_perf_results': True,
      'generate_gtest_json': ActiveMaster.is_production_host,
      'perf_id': 'chromium-rel-linux-64-git',
      'expectations': True,
      'gclient_env': {
        'GYP_DEFINES':
            'target_arch=x64 test_isolation_mode=noop linux_dump_symbols=0',
      },
    }))


def Update(_config, active_master, c):
  return helper.Update(c)
