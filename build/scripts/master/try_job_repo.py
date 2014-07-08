# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.internet import defer

from master.try_job_base import TryJobBase


class TryJobRepoBase(TryJobBase):
  """A base class for try job schedulers based on a repository with patches.

  Used by TryJobSubversion and TryJobGit.
  """
  watcher = None

  def __init__(self, name, pools, properties=None,
               last_good_urls=None, code_review_sites=None):
    TryJobBase.__init__(self, name, pools, properties,
                        last_good_urls, code_review_sites)

  def setServiceParent(self, parent):
    TryJobBase.setServiceParent(self, parent)
    if self.watcher:
      self.watcher.master = self.master
      self.watcher.setServiceParent(self)

  @defer.deferredGenerator
  def addJob(self, options):
    """Submits a job to master to process.

    Resolves revision to LKGR if needed.
    """

    # If there is no revision specified, try finding LKGR.
    if not options.get('revision'):
      wfd = defer.waitForDeferred(self.get_lkgr(options))
      yield wfd
      wfd.getResult()

    wfd = defer.waitForDeferred(self.master.addChange(
        author=','.join(options['email']),
        revision=options['revision'],
        comments=''))
    yield wfd
    change = wfd.getResult()

    self.SubmitJob(options, [change.number])
