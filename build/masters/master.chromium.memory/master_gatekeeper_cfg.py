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
# TODO(glider): browser_tests die unexpectedly on Mac ASan bots
# (http://crbug.com/196533). Because there have been other problems with the
# stability of browser_tests and content_browsertests on the ASan bot, let them
#  not close the tree until the crash rate drops.
categories_steps = {
  '': ['update', 'runhooks'],
  'testers': [
    'base_unittests',
    #'browser_tests',
    'cacheinvalidation_unittests',
    'cc_unittests',
    #'content_browsertests',
    'content_unittests',
    'courgette_unittests',
    'crypto_unittests',
    'device_unittests',
    'gcm_unit_tests',
    'gpu_unittests',
    'installer_util_unittests',
    'ipc_tests',
    'jingle_unittests',
    'media_unittests',
    'mini_installer_test',
    'nacl_integration',
    'net_unittests',
    'ppapi_unittests',
    'printing_unittests',
    'remoting_unittests',
    'sandbox_linux_unittests',
    'sql_unittests',
    'sync_unit_tests',
    'ui_unittests',
    'unit_tests',
    'url_unittests',
   ],
  'compile': ['compile'],
  'crosasantest': ['VMTest'],
}

exclusions = {
}

forgiving_steps = ['update_scripts', 'update', 'gclient_revert']

def Update(config, active_master, c):
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      public_html='../master.chromium/public_html',
      sheriffs=['sheriff'],
      tree_status_url=active_master.tree_status_url,
      use_getname=True))
