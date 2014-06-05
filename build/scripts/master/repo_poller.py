# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import os
import socket
import tempfile
import urllib

from twisted.internet import defer, utils
from twisted.mail import smtp
from twisted.python import log
from buildbot.changes.base import PollingChangeSource
from buildbot.util import deferredLocked

from master.chromium_git_poller_bb8 import GitTagComparator


class RepoTagComparator(GitTagComparator):
  """Maintains a canonical ordering of commits across multiple git repos."""

  def addRevision(self, revision):
    """Unlike GitTagComparator, don't assert(revision not in self.tag_lookup);
    that can legitimately happen if two repos share common history."""
    self.tag_lookup[revision] = len(self.tag_order)
    self.tag_order.append(revision)


class RepoPoller(PollingChangeSource):
  """Polls a repo meta-repository and submits buildbot changes.

  repo is a layer over git that provides support for projects that span multiple
  git repositories.  This poller discovers changes in all of the underlying git
  repositories, and turns them into buildbot master changes.

  Buildbot doesn't provide very good support out of the box for displaying
  changes from multiple git repositories on a single console.  The biggest
  obstacle is that there is no inherent canonical ordering of commits across
  multiple independent repositories.

  This class addresses that by applying and enforcing an arbitrary (but
  generally useful) canonical ordering.  Changes in the git repositories are
  ordered by timestamp first (with one-second granularity).  In the event of
  collisions, ordering falls back to alphabetical ordering by repository name.
  """

  def __init__(self, repo_url, repo_branches=None, workdir=None,
               pollInterval=5*60, repo_bin='repo', git_bin='git',
               category='', project='', revlinktmpl=None,
               encoding='utf-8', from_addr=None, to_addrs=None,
               smtp_host=None):
    # In 'dry_run' mode poller won't fetch the repository.
    # Used when running master smoke tests.
    self.dry_run = 'POLLER_DRY_RUN' in os.environ

    if not workdir:
      workdir = tempfile.mkdtemp(prefix='repo_poller')
      log.msg('RepoPoller: using new working dir %s' % workdir)

    self.repo_url = repo_url
    self.repo_branches = repo_branches or ['master']
    # transition assertion, repo_branch (string) became repo_branches (list)
    assert issubclass(type(self.repo_branches), list), \
      'repo_branches must be a list'
    self.workdir = workdir
    self.pollInterval = pollInterval
    self.repo_bin = repo_bin
    self.git_bin = git_bin
    self.category = category
    self.project = project
    self.revlinktmpl = revlinktmpl
    self.encoding = encoding
    self.from_addr = from_addr
    self.to_addrs = to_addrs
    self.smtp_host = smtp_host
    self.initLock = defer.DeferredLock()
    self.comparator = RepoTagComparator()
    self.changeCount = 0
    self.errCount = 0

  def startService(self):
    if self.dry_run:
      PollingChangeSource.startService(self)
      return

    if not os.path.isabs(self.workdir):
      self.workdir = os.path.join(self.master.basedir, self.workdir)
      log.msg('RepoPoller: using workdir "%s"' % self.workdir)

    if not os.path.exists(os.path.join(self.workdir, '.repo')):
      d = self.initRepository()
      log.msg('RepoPoller: creating new repo checkout in %s' % self.workdir)
    else:
      d = defer.succeed(None)
      log.msg('RepoPoller: using pre-existing repo checkout.')

    d.addCallback(self.initHistory)
    def _success(*unused_args):
      self.comparator.initialized = True
    d.addCallback(_success)
    PollingChangeSource.startService(self)
    def _failure(failure):
      log.msg('RepoPoller: unable to start service.')
      self.stopService()
      return failure
    d.addErrback(_failure)

  def RunRepoCmd(self, args):
    return self.RunCmd(self.repo_bin, args, self.workdir)

  def RunCmd(self, binary, args, path):
    log.msg('RepoPoller: running "%s %s" (in %s)'
            % (binary, ' '.join(args), path))
    d = utils.getProcessOutputAndValue(binary, args, path=path, env=os.environ)
    def _check_status(result):
      (stdout, stderr, status) = result
      if status != 0:
        raise RuntimeError(('failure #%d: "%s" (in %s) failed with exit code '
                            '%d:\n%s\n%s') % (
            self.errCount+1,
            repr([binary] + args),
            path,
            status, stdout, stderr))
      return (stdout, stderr, status)
    d.addCallback(_check_status)
    return d

  @classmethod
  def TagFor(cls, branch_name):
    return 'repo_poller_' + branch_name

  def DoLog(self, unused_result, branch_tag):
    # Make sure that all git repo's have the branch_tag.  Failure indicates the
    # tag already exists on some repo's, which is expected.
    d = self.RunRepoCmd(['forall', '-c', self.git_bin, 'tag', branch_tag])
    d.addErrback(lambda *x: True)
    cb = lambda *x: self.RunRepoCmd(['forall', '-v', '-p', '-c', self.git_bin,
                                     'log', '--format=%H', branch_tag + '..'])
    d.addCallback(cb)
    return d

  def DoCheckoutRepoBranch(self, current_repo_branch):
    init = self.RunRepoCmd(['init', '-b', current_repo_branch])
    # TODO(szager): I pulled the number 4 out of thin air.  Better heuristic?
    init.addCallback(lambda *unused: self.RunRepoCmd(['sync', '-j', '4', '-c']))
    return init

  def DoTag(self, unused_result, branch_tag):
    if self.changeCount == 0:
      return defer.succeed(0)
    self.changeCount = 0
    return self.RunRepoCmd(['forall', '-v', '-c', self.git_bin, 'tag', '-a',
                            '-f', branch_tag, '-m', '"repo poller sync"'])

  @deferredLocked('initLock')
  def initRepository(self):
    if not os.path.exists(self.workdir):
      os.makedirs(self.workdir)
    repo_args = ['init', '-u', '/'.join([self.repo_url, 'manifest'])]
    if self.repo_branches:
      repo_args.extend(['-b', self.repo_branches[0]])  # any branch will do
    d = self.RunRepoCmd(repo_args)
    # Bug 124131
    d.addCallback(lambda *unused: self.RunRepoCmd(['sync', '-j', '4']))
    def _success(*args):
      log.msg('RepoPoller: finished initializing.')
    d.addCallback(_success)
    return d

  @deferredLocked('initLock')
  def initHistory(self, *args):
    d = defer.succeed(0)
    for repo_branch in self.repo_branches:
      log.msg('RepoPoller: initializing revision history for branch '
              + repo_branch)
      d.addCallback(lambda x, b=repo_branch: self.DoCheckoutRepoBranch(b))
      def _log(*args):
        return self.RunRepoCmd(['forall', '-v', '-p', '-c',
                                self.git_bin, 'log', '--format=%H'])
      d.addCallback(_log)
      d.addCallback(self.ProcessInitialHistory)
      def _setChangeCount(*args):
        self.changeCount = 1  # To force DoTag.
      d.addCallback(_setChangeCount)
      d.addCallback(self.DoTag, RepoPoller.TagFor(repo_branch))
    return d

  @deferredLocked('initLock')
  def poll(self):
    if self.dry_run:
      return defer.succeed(None)

    d = defer.succeed(0)
    for repo_branch in self.repo_branches:
      d.addCallback(log.msg,'RepoPoller: polling new changes for branch %s...'
                    % repo_branch)
      d.addCallback(lambda x, b=repo_branch: self.DoCheckoutRepoBranch(b))
      d.addCallback(self.DoLog, RepoPoller.TagFor(repo_branch))
      d.addCallback(self.ProcessChanges, repo_branch)
      d.addCallback(self.DoTag, RepoPoller.TagFor(repo_branch))
      def _success(ret_val, rb=repo_branch):
        log.msg('RepoPoller: finished polling ' + rb)
        self.errCount = 0
      def _failure(failure, rb=repo_branch):
        msg = ('RepoPoller is having problems...\n\n'
               'host: %s\n'
               'repo checkout: %s\n'
               'repo url: %s\n'
               'repo branch: %s\n\n'
               '%s') % (socket.gethostname(), self.workdir, self.repo_url,
                       rb, failure)
        log.err(msg)
        self.errCount += 1
        if self.errCount % 3 == 0 and self.smtp_host and self.to_addrs:
          smtp.sendmail(smtphost=self.smtp_host,
                        from_addr=self.from_addr,
                        to_addrs=self.to_addrs,
                        msg=msg)
        return failure
      d.addCallback(_success)
      d.addErrback(_failure)
    d.addCallback(log.msg, 'Done polling changes for branches in %s'
                  % self.repo_url)
    return d

  def GetCommitComments(self, project, rev):
    args = ['log', rev, '--no-walk', '--format=%s%n%b']
    d = utils.getProcessOutput(self.git_bin, args,
                               path=os.path.join(self.workdir, project),
                               env=os.environ, errortoo=False)
    def process(git_output):
      stripped_output = git_output.strip().decode(self.encoding)
      if len(stripped_output) == 0:
        raise RuntimeError('could not get commit comment for rev')
      return stripped_output
    d.addCallback(process)
    return d

  def GetCommitFiles(self, project, rev):
    args = ['log', rev, '--name-only', '--no-walk', '--format=%n']
    d = utils.getProcessOutput(self.git_bin, args,
                               path=os.path.join(self.workdir, project),
                               env=os.environ, errortoo=False)
    d.addCallback(lambda git_output: [x for x in git_output.splitlines() if x])
    return d

  def GetCommitName(self, project, rev):
    args = ['log', rev, '--no-walk', '--format=%aE']
    d = utils.getProcessOutput(self.git_bin, args,
                               path=os.path.join(self.workdir, project),
                               env=os.environ, errortoo=False)
    def process(git_output):
      stripped_output = git_output.strip().decode(self.encoding)
      if len(stripped_output) == 0:
        raise RuntimeError('RepoPoller: could not get commit name for rev')
      return stripped_output
    d.addCallback(process)
    return d

  def ParseRepoGitLogs(self, stdout):
    """Parse the output of `repo forall -c git log ...`

    Collate new revisions by project, and sort by commit order.
    """
    changes = {}  # changes[project] = [commit, commit, ...]
    project = None
    for line in stdout.splitlines():
      if not line:
        continue
      if line[:8] == 'project ':
        project = line[8:].rstrip('/')
        continue
      assert(project)
      changes.setdefault(project, []).append(line)

    # Put changes in forward commit order, earliest-to-latest.
    for project_changes in changes.itervalues():
      project_changes.reverse()

    for project in sorted(changes):
      for change in changes[project]:
        self.comparator.addRevision(change)

    return changes

  def ProcessInitialHistory(self, args):
    """Initialize comparator with existing commits."""
    (stdout, stderr, status) = args
    if status:
      log.msg('RepoPoller: could not initialize repo history '
              'from git logs: %s.' % stderr)
      return
    self.ParseRepoGitLogs(stdout)

  @defer.deferredGenerator
  def ProcessChanges(self, args, current_repo_branch):
    (stdout, stderr, status) = args
    if status:
      log.msg('RepoPoller: running `git log` '
              'across repo projects failed: %s' % stderr)
      return

    # TODO(szager): In a perfect world, we would use the time these changes were
    # merged into the main repository.  That time is not currently preserved,
    # so we use 'now' instead.  In the future, it would be nice if gerrit were
    # to run filter-branch to reset the committer timestamp to when the patch
    # was applied.
    timestamp = datetime.datetime.utcnow()

    for project, revisions in self.ParseRepoGitLogs(stdout).iteritems():
      for rev in revisions:
        dl = defer.DeferredList([
            self.GetCommitName(project, rev),
            self.GetCommitFiles(project, rev),
            self.GetCommitComments(project, rev),
            ], consumeErrors=True)

        wfd = defer.waitForDeferred(dl)
        yield wfd
        results = wfd.getResult()

        # check for failures
        failures = [r[1] for r in results if not r[0]]
        if failures:
          # just fail on the first error; they're probably all related!
          raise failures[0]

        revlink = ''
        if self.revlinktmpl and rev:
          revlink = self.revlinktmpl % (
              urllib.quote_plus(project), urllib.quote_plus(rev))

        name, files, comments = [r[1] for r in results]
        d = self.master.addChange(
            author=name,
            revision=rev,
            files=files,
            comments=comments,
            when_timestamp=timestamp,
            branch=None,
            category=self.category,
            project=self.project,
            repository='/'.join([self.repo_url, project]),
            revlink=revlink,
            properties={'manifest_url': self.repo_url,
                        'manifest_branch': current_repo_branch})
        wfd = defer.waitForDeferred(d)
        yield wfd
        results = wfd.getResult()
        self.changeCount += 1
