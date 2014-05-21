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

defaults['category'] = '5webkit android latest'

#
# Android scheduler
#
S('s5_android_webkit', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for the builder
#
T('android_rel_trigger')

android_rel_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'webkit_latest_rel')
#
# Android Rel Builder
#
B('Android Builder', 'f_android_rel', scheduler='s5_android_webkit')
F('f_android_rel', linux_android().ChromiumWebkitLatestAnnotationFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_webkit_latest_builder.sh',
    factory_properties={
        'trigger': 'android_rel_trigger',
        'build_url': android_rel_archive,
        }))

B('WebKit Android (GalaxyNexus)', 'f_webkit_android_tests', None,
  'android_rel_trigger', auto_reboot=False)
F('f_webkit_android_tests',
  linux_android().ChromiumWebkitLatestAnnotationFactory(
    annotation_script=('src/build/android/buildbot/'
                       'bb_webkit_latest_webkit_tester.sh'),
    tests=['webkit'],
    factory_properties={
        'build_url': android_rel_archive,
        'archive_webkit_results': True,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        }))
def Update(config, active_master, c):
  return helper.Update(c)
