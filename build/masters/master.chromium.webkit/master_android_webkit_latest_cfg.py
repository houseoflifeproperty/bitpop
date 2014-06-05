# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def linux_android():
  return chromium_factory.ChromiumFactory('',
    'linux2', full_checkout=True, nohooks_on_update=True, target_os='android')


################################################################################
## Release
################################################################################

defaults['category'] = 'layout'

#
# Triggerable scheduler for the builder
#
T('android_rel_trigger')

android_rel_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'webkit_latest_rel')
#
# Android Rel Builder
#
B('Android Builder', 'f_android_rel', scheduler='global_scheduler')
F('f_android_rel', linux_android().ChromiumAnnotationFactory(
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webkit-latest-builder-rel',
        'build_url': android_rel_archive,
        'trigger': 'android_rel_trigger',
        'blink_config': 'blink',
        }))

B('WebKit Android (Nexus4)', 'f_webkit_android_tests', None,
  'android_rel_trigger')
F('f_webkit_android_tests',
  linux_android().ChromiumAnnotationFactory(
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webkit-latest-webkit-tests-rel',
        'archive_webkit_results': ActiveMaster.is_production_host,
        'build_url': android_rel_archive,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
        }))

def Update(_config, _active_master, c):
  return helper.Update(c)
