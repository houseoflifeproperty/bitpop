# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def linux_android():
  return chromium_factory.ChromiumFactory('',
    'linux2', nohooks_on_update=True, target_os='android')


################################################################################
## Release
################################################################################

defaults['category'] = 'nonlayout'

#
# Triggerable scheduler for the builder
#
T('android_dbg_trigger')

android_dbg_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'webkit_latest_dbg')

#
# Android dbg builder
#
B('Android Builder (dbg)', 'f_android_dbg', scheduler='global_scheduler')
F('f_android_dbg', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webkit-latest-builder-dbg',
        'build_url': android_dbg_archive,
        'trigger': 'android_dbg_trigger',
        'prune_limit': 5,
        'blink_config': 'blink',
        }))

B('Android Tests (dbg)', 'f_android_dbg_tests', None, 'android_dbg_trigger',
  auto_reboot=False)
F('f_android_dbg_tests', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webkit-latest-tests-dbg',
        'build_url': android_dbg_archive,
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
