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

def linux_android(): return chromium_factory.ChromiumFactory('',
    'linux2', nohooks_on_update=True, target_os='android')


################################################################################
## Release
################################################################################

defaults['category'] = '9android latest'

#
# Android scheduler
#
S('s9_android_webkit', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for the builder
#
T('android_dbg_trigger')

android_dbg_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'webkit_latest_dbg')

#
# Android dbg builder
#
B('Android Builder (dbg)', 'f_android_dbg', scheduler='s9_android_webkit')
F('f_android_dbg', linux_android().ChromiumWebkitLatestAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_webkit_latest_builder.sh',
    factory_properties={
        'trigger': 'android_dbg_trigger',
        'build_url': android_dbg_archive,
        }))

B('Android Tests (dbg)', 'f_android_dbg_tests', None, 'android_dbg_trigger',
  auto_reboot=False)
F('f_android_dbg_tests', linux_android().ChromiumWebkitLatestAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_webkit_latest_tester.sh',
    factory_properties={'build_url': android_dbg_archive}))

def Update(config, active_master, c):
  return helper.Update(c)
