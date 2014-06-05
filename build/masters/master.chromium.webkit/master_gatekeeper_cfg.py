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
categories_steps = {
  '': ['update', 'runhooks', 'compile'],
}

exclusions = {
  'WebKit XP': ['runhooks'], # crbug.com/262577

  # crbug.com/334617: For now, Oilpan bots don't close the tree.
  'WebKit Linux Oilpan': [],
  'WebKit Linux Oilpan (dbg)': [],
  'WebKit Mac Oilpan': [],
  'WebKit Mac Oilpan (dbg)': [],
  'WebKit Win Oilpan': [],
  'WebKit Win Oilpan (dbg)': [],

  'WebKit Linux Leak': [],
  'WebKit Linux Oilpan Leak': [],
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
      tree_status_url=active_master.tree_status_url,
      use_getname=True,
      sheriffs=['sheriff_webkit']))
