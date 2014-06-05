# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = 'nonlayout'

#
# ChromiumOS Rel Builder
#
B('Linux ChromiumOS Builder', 'f_chromiumos_rel', scheduler='global_scheduler',
    auto_reboot=False)
F('f_chromiumos_rel', linux().ChromiumOSFactory(
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
      'url_unittests',
      'views_unittests',
    ],
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'chromeos=1'},
        'blink_config': 'blink',
    }))


def Update(_config, _active_master, c):
  return helper.Update(c)
