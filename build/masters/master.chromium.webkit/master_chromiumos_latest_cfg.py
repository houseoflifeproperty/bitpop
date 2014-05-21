# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '9linux latest'

#
# Main release scheduler for webkit
#
S('s10_webkit_rel', branch='trunk', treeStableTimer=60)

#
# ChromiumOS Rel Builder
#
B('Linux ChromiumOS Builder', 'f_chromiumos_rel', scheduler='s10_webkit_rel',
    auto_reboot=False)
F('f_chromiumos_rel', linux().ChromiumOSWebkitLatestFactory(
    slave_type='Builder',
    tests=[],
    options=['--compiler=goma',
      'aura_builder',
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'compositor_unittests',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'dbus_unittests',
      'device_unittests',
      'gpu_unittests',
      'googleurl_unittests',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'net_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'views_unittests',
    ],
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'chromeos=1'}
    }))


def Update(config, active_master, c):
  return helper.Update(c)
