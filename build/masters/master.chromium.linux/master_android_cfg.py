# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_config
from master.factory import annotator_factory
from master.factory import chromium_factory

m_annotator = annotator_factory.AnnotatorFactory()

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def linux_android():
  return chromium_factory.ChromiumFactory(
    '', 'linux2', nohooks_on_update=True, target_os='android')

defaults['category'] = '5android'

android_dbg_archive = master_config.GetArchiveUrl(
    'ChromiumLinux',
    'Android Builder (dbg)',
    'Android_Builder__dbg_',
    'linux')

android_rel_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'android_main_rel')

#
# Main release scheduler for src/
#
S('android', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the builder
#
T('android_trigger_dbg')
T('android_trigger_rel')

#
# Android Builder
#
B('Android Builder (dbg)', 'f_android_dbg', 'android', 'android',
  auto_reboot=False, notify_on_missing=True)
F('f_android_dbg', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'main-builder-dbg',
      'trigger': 'android_trigger_dbg',
    }))

B('Android Tests (dbg)', 'f_android_dbg_tests', 'android',
  'android_trigger_dbg', notify_on_missing=True)
F('f_android_dbg_tests', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'main-tests-dbg',
      'build_url': android_dbg_archive,
    }))

B('Android Builder', 'f_android_rel', 'android', 'android',
  notify_on_missing=True)
F('f_android_rel', linux_android().ChromiumAnnotationFactory(
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'main-builder-rel',
      'build_url': android_rel_archive,
      'trigger': 'android_trigger_rel',
    }))

B('Android Tests', 'f_android_rel_tests', 'android', 'android_trigger_rel',
  notify_on_missing=True)
F('f_android_rel_tests', linux_android().ChromiumAnnotationFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'main-tests-rel',
      'build_url': android_rel_archive,
    }))

B('Android Clang Builder (dbg)', 'f_android_clang_dbg', 'android', 'android',
  notify_on_missing=True)
F('f_android_clang_dbg', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'main-clang-builder-dbg',
    }))

B('Android Webview AOSP Builder', 'f_android_webview_aosp_rel', 'android',
  'android', notify_on_missing=True)
F('f_android_webview_aosp_rel',
  m_annotator.BaseFactory('android_webview_aosp'))


def Update(_config_arg, _active_master, c):
  helper.Update(c)

  specs = [
    {'name': 'Android GN', 'recipe': 'chromium_gn'},
  ]

  c['schedulers'].extend([
      SingleBranchScheduler(name='android_gn',
                            branch='src',
                            treeStableTimer=60,
                            builderNames=['Android GN']),
  ])
  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
              spec.get('recipe', 'chromium'),
              factory_properties=spec.get('factory_properties'),
              triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '5android',
      } for spec in specs
  ])
