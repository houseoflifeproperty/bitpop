# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status.builder import FAILURE
from master import chromium_notifier
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, the blame list will be notified.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': [
    'update',
    'runhooks',
    'gn',
    'compile',
    'Presubmit',
    'Static-Initializers',
    'Check',
    'OptimizeForSize',
    'Mjsunit',
    'Webkit',
    'Benchmarks',
    'Test262',
    'Mozilla',
    'GCMole',
    'Fuzz',
    'Deopt Fuzz',
    # TODO(machenbach): Enable mail notifications as soon as a try builder is
    # set up.
    # 'webkit_tests',
  ],
  'asan': [
    'browser_tests',
    'net',
    'media',
    'remoting',
    'content_browsertests',
  ]
}

exclusions = {
  'V8 Linux - mips - sim': ['compile'],
  'V8 Linux - x87 - nosnap - debug': [],
  'V8 Linux - predictable': [],
  'V8 Linux - git': [],
  'V8 Linux64 TSAN': ['Check'],
  'NaCl V8 Linux': ['Check'],
  'NaCl V8 Linux64 - stable': ['Check'],
  'NaCl V8 Linux64 - canary': ['Check'],
  'Webkit - dbg': ['webkit_tests'],
  'Webkit Mac - dbg': ['webkit_tests'],
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'gclient_revert']

x87_categories_steps = {'x87': ['runhooks', 'compile', 'Check']}

class V8Notifier(chromium_notifier.ChromiumNotifier):
  def isInterestingStep(self, build_status, step_status, results):
    """Watch only failing steps."""
    return results[0] == FAILURE


def Update(config, active_master, c):
  c['status'].append(V8Notifier(
      fromaddr=active_master.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      sendToInterestedUsers=True,
      status_header='buildbot failure in %(project)s on %(builder)s, %(steps)s',
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps))
  c['status'].append(V8Notifier(
      fromaddr=active_master.from_address,
      categories_steps=x87_categories_steps,
      exclusions={},
      relayhost=config.Master.smtp,
      sendToInterestedUsers=False,
      extraRecipients=['weiliang.lin@intel.com', 'chunyang.dai@intel.com'],
      status_header='buildbot failure in %(project)s on %(builder)s, %(steps)s',
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps))
