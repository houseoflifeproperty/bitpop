# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import gitpoller
from buildbot.status.web.console import RevisionComparator
from buildbot.util import deferredLocked
from twisted.python import log
from twisted.internet import defer, utils

import os


class GitTagComparator(RevisionComparator):
  """Tracks the commit order of tags in a git repository.
  This class explicitly does NOT support any kind of branching; it assumes
  a strictly linear commit history."""

  def __init__(self):
    """Set up two data structures:
         self.tag_order is an in-order list of all commit tags in the repo.
         self.tag_lookup maps tags to their index in self.tag_order."""
    super(GitTagComparator, self).__init__()
    self.initialized = False
    self.tag_order = []
    self.tag_lookup = {}

  def addRevision(self, revision):
    assert revision not in self.tag_lookup
    self.tag_lookup[revision] = len(self.tag_order)
    self.tag_order.append(revision)

  def tagcmp(self, x, y):
    """A general-purpose sorting comparator for git tags
    based on commit order."""
    try:
      return cmp(self.tag_lookup[x], self.tag_lookup[y])
    except KeyError, e:
      msg = 'GitTagComparator doesn\'t know anything about git tag %s' % str(e)
      raise RuntimeError(msg)

  def isRevisionEarlier(self, first, second):
    return self.tagcmp(first.revision, second.revision) < 0

  def isValidRevision(self, revision):
    return revision in self.tag_lookup

  def getSortingKey(self):
    return lambda x: self.tag_lookup[x.revision]


class ChromiumGitPoller(gitpoller.GitPoller):
  """A git poller which keeps track of commit tag order.
  This class has the same outward behavior as GitPoller, but it also keeps
  track of the commit order of git tags."""

  def __init__(self, *args, **kwargs):
    """Do not use /tmp as the default work dir, use the master checkout
    directory.
    """
    # In 'dry_run' mode poller won't fetch the repository.
    # Used when running master smoke tests.
    if 'dry_run' in kwargs:
      self.dry_run = kwargs.pop('dry_run')
    else:
      self.dry_run = 'POLLER_DRY_RUN' in os.environ
    if not kwargs.get('workdir'):
      # Make it non-absolute so it's set relative to the master's directory.
      kwargs['workdir'] = 'git_poller_%s' % os.path.basename(kwargs['repourl'])
    gitpoller.GitPoller.__init__(self, *args, **kwargs)
    self.comparator = GitTagComparator()

  # We override _get_commit_name to remove the SVN UUID from commiter emails.
  def _get_commit_name(self, rev):
    args = ['log', rev, '--no-walk', r'--format=%aE']
    d = utils.getProcessOutput(
      self.gitbin, args, path=self.workdir, env=os.environ, errortoo=False)
    def process(git_output):
      stripped_output = git_output.strip().decode(self.encoding)
      if not stripped_output:
        raise EnvironmentError('could not get commit name for rev')
      # Return just a standard email address.
      tokens = stripped_output.split('@')
      return '@'.join(tokens[:2])
    d.addCallback(process)
    return d

  def _parse_history(self, res):
    new_history = [line[0:40] for line in res[0].splitlines()]
    log.msg("Parsing %d new git tags" % len(new_history))
    new_history.reverse()  # We want earliest -> latest
    for revision in new_history:
      self.comparator.addRevision(revision)

  @deferredLocked('initLock')
  def _init_history(self, _):
    """Initialize tag order data from an existing git checkout.
    This is invoked once, when the git poller is started."""
    log.msg('ChromiumGitPoller: initializing revision history')
    d = utils.getProcessOutputAndValue(
        self.gitbin,
        ['log', 'origin/%s' % self.branch, r'--format=%H'],
        path=self.workdir, env=dict(PATH=os.environ['PATH']))
    d.addCallback(self._convert_nonzero_to_failure)
    d.addErrback(self._stop_on_failure)
    d.addCallback(self._parse_history)
    return d

  def _process_history(self, res):
    """Add new git commits to the tag order data.
    This is called every time the poller detects new changes."""
    d = utils.getProcessOutputAndValue(
      self.gitbin,
      ['log', '%s..origin/%s' % (self.branch, self.branch), r'--format=%H'],
      path=self.workdir, env=dict(PATH=os.environ['PATH']))
    d.addCallback(self._convert_nonzero_to_failure)
    d.addErrback(self._stop_on_failure)
    d.addCallback(self._parse_history)
    return d

  @staticmethod
  def _process_history_failure(res):
    log.msg('ChromiumGitPoller: repo log failed')
    log.err(res)
    return None

  def startService(self):
    gitpoller.GitPoller.startService(self)
    d = defer.succeed(None)
    if not self.dry_run:
      d.addCallback(self._init_history)
    def _comparator_initialized(*unused_args):
      self.comparator.initialized = True
    d.addCallback(_comparator_initialized)

  @deferredLocked('initLock')
  def poll(self):
    if self.dry_run:
      return defer.succeed(None)
    d = self._get_changes()
    d.addCallback(self._process_history)
    d.addErrback(ChromiumGitPoller._process_history_failure)
    d.addCallback(self._process_changes)
    d.addErrback(self._process_changes_failure)
    d.addCallback(self._catch_up)
    d.addErrback(self._catch_up_failure)
    return d

  def initRepository(self):
    if self.dry_run:
      return defer.succeed(None)
    else:
      return gitpoller.GitPoller.initRepository(self)
