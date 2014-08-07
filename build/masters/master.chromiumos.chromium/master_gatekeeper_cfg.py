# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import chromium_notifier
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
gardener_categories_steps = {
  '': [],
  'pfq': ['cbuildbot'],
}

memory_categories_steps = {
  '': [],
  'crosasantest': ['VMTest'],
}

trooper_categories_steps = {
  '': ['update_scripts', 'Clear and Clone chromite'],
}

exclusions = {
}

forgiving_steps = ['update_scripts', 'update', 'gclient_revert']

warning_header = ('Please look at failure in "%(steps)s" on "%(builder)s" '
                  'and help out if you can')


def Update(config, active_master, c):
  c['status'].append(chromium_notifier.ChromiumNotifier(
      fromaddr=active_master.from_address,
      categories_steps=gardener_categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      status_header=warning_header,
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      public_html='../master.chromiumos/public_html',
      sheriffs=['sheriff_cr_cros_gardeners'],
      use_getname=True))
  c['status'].append(chromium_notifier.ChromiumNotifier(
      fromaddr=active_master.from_address,
      categories_steps=memory_categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      status_header=warning_header,
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      public_html='../master.chromiumos/public_html',
      sheriffs=['sheriff_memory'],
      use_getname=True))
  c['status'].append(chromium_notifier.ChromiumNotifier(
      fromaddr=active_master.from_address,
      categories_steps=trooper_categories_steps,
      relayhost=config.Master.smtp,
      status_header='%(steps)s failed on "%(builder)s"',
      subject='buildbot trooper alert on %(builder)s (%(projectName)s)',
      extraRecipients=['chrome-troopers@google.com'],
      sheriffs=[],
      lookup=master_utils.FilterDomain(),
      use_getname=True))

