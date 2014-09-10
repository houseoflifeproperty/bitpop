# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import svnpoller

from common import chromium_utils

from master import build_utils
from master import gitiles_poller

import config

def ChromeTreeFileSplitter(path):
  """split_file for the 'src' project in the trunk."""

  # Exclude .DEPS.git from triggering builds on chrome.
  if path == 'src/.DEPS.git':
    return None

  # List of projects we are interested in. The project names must exactly
  # match paths in the Subversion repository, relative to the 'path' URL
  # argument. build_utils.SplitPath() will use them as branch names to
  # kick off the Schedulers for different projects.
  projects = ['src']
  return build_utils.SplitPath(projects, path)


class _ChromiumSvnPoller(svnpoller.SVNPoller):
  def __init__(self, svnurl=None, svnbin=None, split_file=None,
               pollinterval=None, revlinktmpl=None,
               *args, **kwargs):
    if svnurl is None:
      svnurl = config.Master.trunk_url

    if svnbin is None:
      svnbin = chromium_utils.SVN_BIN

    if split_file is None:
      split_file = ChromeTreeFileSplitter

    if revlinktmpl is None:
      revlinktmpl = (
          'http://src.chromium.org/viewvc/chrome?view=rev&revision=%s')

    if pollinterval is None:
      pollinterval = 10

    svnpoller.SVNPoller.__init__(
        self, svnurl=svnurl, svnbin=svnbin, split_file=split_file,
        pollinterval=pollinterval, revlinktmpl=revlinktmpl, *args, **kwargs)


def _ChromiumChangeFilter(commit_json, branch):
  if 'tree_diff' not in commit_json:
    return True
  if (len(commit_json.get('tree_diff', [])) == 1 and
      commit_json['tree_diff'][0]['new_path'] == '.DEPS.git'):
    return False
  return True


def ChromiumSvnPoller(svnurl=None, *args, **kwargs):
  cachepath = kwargs.pop('cachepath', None)
  pollInterval = kwargs.pop('pollinterval', 10)
  project = kwargs.pop('project', None)
  if svnurl is None:
    svnurl = config.Master.trunk_url
  if svnurl == config.Master.trunk_url and not args and not kwargs:
    poller_kwargs = {
        'repo_url': config.Master.git_server_url + '/chromium/src',
        'branches': ['master'],
        'revlinktmpl':
            'http://src.chromium.org/viewvc/chrome?view=rev&revision=%s',
        'pollInterval': pollInterval,
        'svn_mode': True,
        'change_filter': _ChromiumChangeFilter,
    }
    if project and project != 'src':
      poller_kwargs['svn_branch'] = 'src'
    return gitiles_poller.GitilesPoller(**poller_kwargs)
  kwargs.update([
      ('cachepath', cachepath),
      ('pollinterval', pollInterval),
      ('project', project),
  ])
  return _ChromiumSvnPoller(svnurl, *args, **kwargs)
