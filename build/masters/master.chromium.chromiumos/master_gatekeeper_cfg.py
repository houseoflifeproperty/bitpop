# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gatekeeper
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
chromium_categories_steps = {
  '': ['steps', 'update', 'runhooks'],
  'tester': [
    'app_list_unittests',
    'aura_unit_tests',
    'base_unittests',
    'browser_tests',
    'cacheinvalidation_unittests',
    'chromeos_unittests',
    'components_unittests',
    'content_browsertests',
    'content_unittests',
    'courgette_unittests',
    'crypto_unittests',
    'dbus_unittests',
    'device_unittests',
    'google_apis_unittests',
    'installer_util_unittests',
    'interactive_ui_tests',
    'ipc_tests',
    'jingle_unittests',
    'keyboard_unittests',
    'media_unittests',
    'message_center_unittests',
    'nacl_integration',
    'nacl_loader_unittests',
    'net_unittests',
    'ppapi_unittests',
    'printing_unittests',
    'remoting_unittests',
    'sbox_integration_tests',
    'sbox_unittests',
    'sbox_validation_tests',
    'sizes',
    'sql_unittests',
    'start_crash_handler',
    'sync_unittests',
    'ui_unittests',
    'unit_tests',
    'url_unittests',
    'views_unittests',
    #'webkit_tests',
   ],
  'compile': ['check_deps', 'compile', 'archive_build'],
}

exclusions = {
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'archive_build', 'start_crash_handler', 'gclient_revert']

subject = ('buildbot %(result)s in %(projectName)s on %(builder)s, '
           'revision %(revision)s')

def Update(config, active_master, c):
  # chrome likely/possible failures to the chrome sheriffs, closing the
  # chrome tree
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=chromium_categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject=subject,
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      tree_status_url=active_master.tree_status_url,
      sheriffs=['sheriff'],
      public_html='../master.chromium/public_html',
      use_getname=True))
