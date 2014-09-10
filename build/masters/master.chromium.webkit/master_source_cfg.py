# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import svnpoller
from buildbot.scheduler import AnyBranchScheduler

from common import chromium_utils

from master import build_utils
from master import chromium_svn_poller

def WebkitFileSplitter(path):
  """split_file for webkit.org repository."""
  projects = ['trunk']
  return build_utils.SplitPath(projects, path)


def Update(config, _active_master, c):
  # Polls config.Master.trunk_url for changes
  cr_poller = chromium_svn_poller.ChromiumSvnPoller(pollinterval=30,
                                                    cachepath='chromium.svnrev',
                                                    project='chromium')
  c['change_source'].append(cr_poller)

  webkit_url = 'http://src.chromium.org/viewvc/blink?view=rev&revision=%s'
  webkit_poller = svnpoller.SVNPoller(svnurl = config.Master.webkit_root_url,
                                      svnbin=chromium_utils.SVN_BIN,
                                      split_file=WebkitFileSplitter,
                                      pollinterval=30,
                                      revlinktmpl=webkit_url,
                                      cachepath='webkit.svnrev',
                                      project='webkit')
  c['change_source'].append(webkit_poller)

  c['schedulers'].append(AnyBranchScheduler(
      name='global_scheduler', branches=['trunk', 'src'], treeStableTimer=60,
      builderNames=[]))

  c['schedulers'].append(AnyBranchScheduler(
      name='global_deps_scheduler', branches=['src'], treeStableTimer=60,
      builderNames=[]))
