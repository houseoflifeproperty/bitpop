# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import annotator_factory
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumLKGR

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.URLScheduler

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def win_out(): return chromium_factory.ChromiumFactory('src/out', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')
def linux_android(): return chromium_factory.ChromiumFactory(
    'src/out', 'linux2', nohooks_on_update=True, target_os='android')

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = '1lkgr'

# Global scheduler
S(name='chromium_lkgr', url=ActiveMaster.poll_url, include_revision=True)

################################################################################
## Windows
################################################################################

B('Win', 'win_full', 'compile|windows', 'chromium_lkgr')
F('win_full', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    factory_properties={'archive_build': ActiveMaster.is_production_host,
                        'gs_bucket': 'gs://chromium-browser-continuous',
                        'gs_acl': 'public-read',
                        'gclient_env': {
                          'GYP_LINK_CONCURRENCY_MAX': '4',
                        },
                       }))

B('Win x64', 'win_x64_full', 'windows', 'chromium_lkgr')
F('win_x64_full', win_out().ChromiumFactory(
    clobber=True,
    compile_timeout=9600,  # Release build is LOOONG
    target='Release_x64',
    options=['--build-tool=ninja', '--', 'all'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gclient_env': {
        'GYP_DEFINES': 'component=static_library target_arch=x64',
        'GYP_LINK_CONCURRENCY_MAX': '4',
      },
      'gs_bucket': 'gs://chromium-browser-continuous',
      'gs_acl': 'public-read',
    }))

################################################################################
## Mac
################################################################################

B('Mac', 'mac_full', 'compile|testers', 'chromium_lkgr')
F('mac_full', mac().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': ActiveMaster.is_production_host,
                        'gs_bucket': 'gs://chromium-browser-continuous',
                        'gs_acl': 'public-read',}))

B('Mac ASAN Release', 'mac_asan_rel', 'compile', 'chromium_lkgr')
F('mac_asan_rel', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', '--', '-target', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': 'asan=1 '}}))

B('Mac ASAN Debug', 'mac_asan_dbg', 'compile', 'chromium_lkgr')
F('mac_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', '--', '-target', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': 'asan=1 component=static_library '}}))

################################################################################
## Linux
################################################################################

B('Linux', 'linux_full', 'compile|testers', 'chromium_lkgr')
F('linux_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': ActiveMaster.is_production_host,
                        'gs_bucket': 'gs://chromium-browser-continuous',
                        'gs_acl': 'public-read',}))

B('Linux x64', 'linux64_full', 'compile|testers', 'chromium_lkgr')
F('linux64_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={
        'archive_build': ActiveMaster.is_production_host,
        'gs_bucket': 'gs://chromium-browser-continuous',
        'gs_acl': 'public-read',
        'gclient_env': {'GYP_DEFINES':'target_arch=x64'}}))

asan_rel_gyp = ('asan=1 lsan=1 asan_coverage=1 use_allocator=none '
                'v8_enable_verify_heap=1 enable_ipc_fuzzer=1 '
                'release_extra_cflags="-gline-tables-only"')

B('ASAN Release', 'linux_asan_rel', 'compile', 'chromium_lkgr')
F('linux_asan_rel', linux().ChromiumASANFactory(
    compile_timeout=2400,  # We started seeing 29 minute links, bug 360158
    clobber=True,
    options=['--compiler=clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_rel_gyp}}))

asan_rel_sym_gyp = ('asan=1 lsan=1 asan_coverage=1 use_allocator=none '
                    'v8_enable_verify_heap=1 enable_ipc_fuzzer=1 '
                    'release_extra_cflags="-gline-tables-only -O1 '
                    '-fno-inline-functions -fno-inline"')

B('ASAN Release (symbolized)', 'linux_asan_rel_sym', 'compile', 'chromium_lkgr')
F('linux_asan_rel_sym', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan-symbolized',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_rel_sym_gyp}}))

asan_debug_gyp = ('asan=1 lsan=1 asan_coverage=1 use_allocator=none '
                  'enable_ipc_fuzzer=1')

B('ASAN Debug', 'linux_asan_dbg', 'compile', 'chromium_lkgr')
F('linux_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_debug_gyp}}))

asan_ia32_v8_arm = ('asan=1 asan_coverage=1 use_allocator=none disable_nacl=1 '
                    'v8_target_arch=arm host_arch=x86_64 target_arch=ia32 '
                    'sysroot=/var/lib/chroot/precise32bit chroot_cmd=precise32 '
                    'v8_enable_verify_heap=1 enable_ipc_fuzzer=1')

asan_ia32_v8_arm_rel_sym = ('%s release_extra_cflags="-gline-tables-only -O1 '
                            '-fno-inline-functions -fno-inline"' %
                            asan_ia32_v8_arm)
asan_ia32_v8_arm_rel = ('%s release_extra_cflags="-gline-tables-only"' %
                        asan_ia32_v8_arm)

# The build process is described at
# https://sites.google.com/a/chromium.org/dev/developers/testing/addresssanitizer#TOC-Building-with-v8_target_arch-arm
B('ASan Debug (32-bit x86 with V8-ARM)',
  'linux_asan_dbg_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_dbg_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-v8-arm',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm}}))

B('ASan Release (32-bit x86 with V8-ARM)',
  'linux_asan_rel_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-v8-arm',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm_rel}}))

B('ASan Release (32-bit x86 with V8-ARM, symbolized)',
  'linux_asan_rel_sym_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_sym_ia32_v8_arm', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_subdir_suffix': 'v8-arm',
       'cf_archive_name': 'asan-symbolized-v8-arm',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_ia32_v8_arm_rel_sym}}))

# The build process for TSan is described at
# http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
tsan_gyp = ('tsan=1 use_allocator=none disable_nacl=1 '
            'debug_extra_cflags="-gline-tables-only" '
            'release_extra_cflags="-gline-tables-only" ')

B('TSAN Release', 'linux_tsan_rel', 'compile', 'chromium_lkgr')
F('linux_tsan_rel', linux().ChromiumFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'tsan',
       'gs_bucket': 'gs://chromium-browser-tsan',
       'gs_acl': 'public-read',
       'tsan': True,
       'gclient_env': {'GYP_DEFINES': tsan_gyp}}))

B('TSAN Debug', 'linux_tsan_dbg', 'compile', 'chromium_lkgr')
F('linux_tsan_dbg', linux().ChromiumFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'tsan',
       'gs_bucket': 'gs://chromium-browser-tsan',
       'gs_acl': 'public-read',
       'tsan': True,
       'gclient_env': {'GYP_DEFINES': tsan_gyp}}))

# This is a bot that uploads LKGR telemetry harnesses to Google Storage.
B('Telemetry Harness Upload', 'telemetry_harness_upload', None, 'chromium_lkgr')
F('telemetry_harness_upload',
  m_annotator.BaseFactory('perf/telemetry_harness_upload'))

################################################################################
## Android
################################################################################

B('Android', 'android', None, 'chromium_lkgr')
F('android', linux_android().ChromiumAnnotationFactory(
    clobber=True,
    target='Release',
    factory_properties={
      'android_bot_id': 'lkgr-clobber-rel',
      'archive_build': True,
      'gs_acl': 'public-read',
      'gs_bucket': 'gs://chromium-browser-continuous',
      'perf_id': 'android-release',
      'show_perf_results': True,
    },
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    ))


def Update(_config, active_master, c):
  return helper.Update(c)
