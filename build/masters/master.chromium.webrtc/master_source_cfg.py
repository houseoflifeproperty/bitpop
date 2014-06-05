# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common import chromium_utils

from master import build_utils

from buildbot.changes import svnpoller


def ChromiumFileSplitter(path):
  """Splits the SVN path into branch and filename sections."""

  # List of projects we are interested in. The project names must exactly
  # match paths in the Subversion repository, relative to the 'path' URL
  # argument. build_utils.SplitPath() will use them as branch names to
  # kick off the Schedulers for different projects.
  projects = ['src']
  return build_utils.SplitPath(projects, path)

def Update(config, c):
  poller = svnpoller.SVNPoller(
      svnurl=config.Master.trunk_url,
      svnbin=chromium_utils.SVN_BIN,
      split_file=ChromiumFileSplitter,
      pollinterval=30,
      revlinktmpl='http://src.chromium.org/viewvc/chrome?view=rev&revision=%s')
  c['change_source'].append(poller)
