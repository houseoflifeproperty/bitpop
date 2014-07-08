# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

from buildbot.changes import svnpoller
from twisted.internet import defer
from twisted.python import log

from common import chromium_utils

from master.try_job_base import text_to_dict
from master.try_job_repo import TryJobRepoBase


class SVNPoller(svnpoller.SVNPoller):
  """A hook in svnpoller.SVNPoller for TryJobSubversion.

  This class is intentionally minimalistic. It does nothing but delegate
  change process to TryJobSubversion.
  """
  def __init__(self, try_job, **kwargs):
    svnpoller.SVNPoller.__init__(self, **kwargs)
    self.try_job = try_job

  def submit_changes(self, changes):
    """Passes the changes to TryJobSubversion.

    Instead of submitting the changes to the master, pass them to
    TryJobSubversion. We don't want buildbot to see these changes.
    """
    return self.try_job.process_svn_changes(changes)


class TryJobSubversion(TryJobRepoBase):
  """Poll a Subversion server to grab patches to try."""
  def __init__(self, name, pools, svn_url, properties=None,
               last_good_urls=None, code_review_sites=None):
    TryJobRepoBase.__init__(self, name, pools, properties, last_good_urls,
                            code_review_sites)
    self.watcher = SVNPoller(self,
                             svnurl=svn_url,
                             svnbin=chromium_utils.SVN_BIN,
                             pollinterval=10)

  @defer.deferredGenerator
  def process_svn_changes(self, changes):
    """For each change submit a job"""
    for change in changes:
      # pylint: disable=E1101
      options = self.parse_options(text_to_dict(change['comments']))

      # Generate patch_url.
      diff_filename = findSingleDiff(change['files'])
      patch_url = ('%s/%s@%s' % (
          self.watcher.svnurl,
          urllib.quote(diff_filename),
          change['revision'])
      )
      options['patch_url'] = patch_url
      options['patch_storage'] = 'svn'

      # Read patch contents.
      wfd = defer.waitForDeferred(self.watcher.getProcessOutput(
          ['cat', patch_url, '--non-interactive']))
      yield wfd
      options['patch'] = wfd.getResult()

      self.addJob(options)


def findSingleDiff(files):
  """Find the only .diff file"""
  # Implicitly skips over non-files like directories.
  diffs = [f for f in files if f.endswith(".diff")]
  if len(diffs) != 1:
    # We only accept changes with 1 diff file.
    log.msg("Try job with too many files %s" % (','.join(files)))
  return diffs[0]
