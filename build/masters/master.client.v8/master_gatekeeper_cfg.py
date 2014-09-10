# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gatekeeper
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': ['update', 'runhooks', 'gn', 'compile'],
  'testers': [
    'Presubmit',
    'Static-Initializers',
    'Check',
    'OptimizeForSize',
    'Webkit',
    'Benchmarks',
    'Test262',
    'Mozilla',
    'GCMole',
   ],
}

exclusions = {
  'V8 Linux - mips - sim': ['compile'],
  'V8 Linux - x87 - nosnap - debug': [],
  'V8 Linux - git': [],
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'gclient_revert']

def Update(config, active_master, c):
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup='google.com',
      forgiving_steps=forgiving_steps,
      tree_status_url=active_master.tree_status_url))
