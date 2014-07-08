# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from twisted.internet import defer, utils
from twisted.python import log

from common import chromium_utils

from master.chromium_git_poller_bb8 import ChromiumGitPoller
from master.try_job_base import text_to_dict
from master.try_job_repo import TryJobRepoBase

class GitPoller(ChromiumGitPoller):
  """A hook in gitpoller.GitPoller for TryJobGit.

  This class is intentionally minimalistic. It does nothing but delegates
  change processing to TryJobGit.
  """
  def __init__(self, try_job, **kwargs):
    ChromiumGitPoller.__init__(self, **kwargs)
    self.try_job = try_job

  def add_change(self, **kwargs):
    """Passes the changes to TryJobGit.

    Instead of submitting the change to the master, pass them to
    TryJobGit. We don't want buildbot to see these changes.
    """
    return self.try_job.process_commit(**kwargs)


class TryJobGit(TryJobRepoBase):
  """Poll a Git server to grab patches to try."""
  def __init__(self, name, pools, git_url, properties=None, workdir=None,
               last_good_urls=None, code_review_sites=None):
    TryJobRepoBase.__init__(
        self,
        name=name,
        pools=pools,
        properties=properties,
        last_good_urls=last_good_urls,
        code_review_sites=code_review_sites)
    self.git_url = git_url
    self.watcher = GitPoller(
        self,
        repourl=git_url,
        workdir=workdir,
        gitbin=chromium_utils.GIT_BIN,
        pollinterval=10)

  def getProcessOutput(self, args):
    return utils.getProcessOutput(self.watcher.gitbin, args,
                                  path=self.watcher.workdir, env=os.environ)

  @defer.deferredGenerator
  def process_commit(self, author, revision, files, comments, when_timestamp,
                     revlink):
    log.msg('TryJobGit: processing change %s' % revision)
    # pylint: disable=E1101
    options = self.parse_options(text_to_dict(comments))

    # Read ref name from the 'ref' file in the master branch.
    # A slave will pull this ref.
    wfd = defer.waitForDeferred(
        self.getProcessOutput(['show', '%s:ref' % revision]))
    yield wfd
    options['patch_ref'] = wfd.getResult()
    options['patch_repo_url'] = self.git_url
    options['patch_storage'] = 'git'

    self.addJob(options)
