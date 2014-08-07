# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Classes for polling a git repository via the gitiles web interface.

The advantage of using gitiles is that a local clone is not needed."""

import time
import urllib
from urlparse import urlparse

from buildbot.status.web.console import RevisionComparator
from buildbot.changes.base import PollingChangeSource
from buildbot.util import epoch2datetime
from twisted.internet import defer
from twisted.python import log

from common.gerrit_agent import GerritAgent


LOG_TEMPLATE = '%s/+log/%s?format=JSON&n=%d'
REVISION_DETAIL_TEMPLATE = '%s/+/%s?format=JSON'


def _always_unlock(result, lock):
  lock.release()
  return result


class GitilesRevisionComparator(RevisionComparator):
  """Tracks the commit order of tags in a git repository.

  This class explicitly does NOT support any kind of branching; it assumes
  a strictly linear commit history."""

  def __init__(self, repo_path, branch, agent, init_cb=None):
    super(GitilesRevisionComparator, self).__init__()
    self.repo_path = urllib.quote(repo_path)
    self.agent = agent
    self.min_idx = 0
    self.max_idx = 0
    self.sha1_lookup = {}
    self.initialized = False
    d = self._fetch(branch)
    def _set_initialized(_):
      self.initialized = True
      return True
    d.addCallback(_set_initialized)
    if init_cb:
      d.addCallback(init_cb)

  def _fetch(self, revision):
    path = LOG_TEMPLATE % (self.repo_path, revision, 10000)
    d = self.agent.request('GET', path, retry=5)
    d.addCallback(self._process_log)
    return d

  def _process_log(self, log_json):
    for commit in log_json['log']:
      sha1 = commit['commit']
      assert sha1 not in self.sha1_lookup
      self.min_idx -= 1
      self.sha1_lookup[sha1] = self.min_idx
    next_sha1 = log_json.get('next', None)
    if next_sha1:
      return self._fetch(next_sha1)
    return defer.succeed(None)

  def addRevision(self, revision):
    assert revision not in self.sha1_lookup
    self.sha1_lookup[revision] = self.max_idx
    self.max_idx += 1

  def tagcmp(self, x, y):
    return cmp(self.sha1_lookup[x], self.sha1_lookup[y])

  def isValidRevision(self, revision):
    return revision in self.sha1_lookup

  def isRevisionEarlier(self, first_change, second_change):
    return self.tagcmp(first_change, second_change) < 0

  def getSortingKey(self):
    return self.sha1_lookup.__getitem__


class GitilesPoller(PollingChangeSource):
  """Polls a git repository using the gitiles web interface. """

  def __init__(
      self, repo_url, branch='master', pollInterval=10*60, category=None,
      project=None, revlinktmpl=None, agent=None):
    """Args:

    repo_url: URL of the gitiles service to be polled.
    branch: Git repository branch to be polled.
    pollInterval: Number of seconds between polling operations.
    category: Category to be applied to generated Change objects.
    project: Project to be applied to generated Change objects.
    revlinktmpl: String template, taking a single 'revision' parameter, used to
        generate a web link to a revision.
    agent: A GerritAgent object used to make requests to the gitiles service.
    """

    u = urlparse(repo_url)
    self.repo_url = repo_url
    self.repo_host = u.netloc
    self.repo_path = urllib.urlquote(u.path)
    self.branch = branch
    self.pollInterval = pollInterval
    self.category = category
    self.project = project
    self.revlinktmpl = revlinktmpl
    if agent is None:
      agent = GerritAgent(repo_url, read_only=True)
    self.agent = agent
    self.comparator = GitilesRevisionComparator(
        self.repo_path, branch, self.agent)
    self.lock = defer.deferredLock()
    self.last_head = None

  def _create_change(self, commit_json):
    if not commit_json:
      return
    commit_author = commit_json['author']['email']
    commit_tm = commit_json['committer']['time']
    commit_tm = time.strptime(commit_tm.partition('+')[0].strip())
    commit_files = []
    if 'tree_diff' in commit_json:
      commit_files = [
          x['new_path'] for x in commit_json['tree_diff'] if 'new_path' in x]
    commit_msg = commit_json['message']
    revlink = ''
    if self.revlinktmpl and commit_json['commit']:
      revlink = self.revlinktmpl % commit_json['commit']
    return self.master.addChange(
        author=commit_author,
        revision=commit_json['commit'],
        files=commit_files,
        comments=commit_msg,
        when_timestamp=epoch2datetime(commit_tm),
        branch=self.branch,
        category=self.category,
        project=self.project,
        repository=self.repo_url,
        revlink=revlink)

  def _process_log(self, log_json):
    if not log_json['log']:
      return
    if 'next' in log_json:
      log_spec = '%s..%s' % (self.last_head, log_json['next'])
      path = LOG_TEMPLATE % (self.repo_path, log_spec, 100)
      d = self.agent.request('GET', path, retry=5)
      d.addCallback(self._process_log)
      d.addCallback(lambda _: self._process_log(log_json))
      return d
    self.last_head = log_json['log'][0]['commit']
    d = defer.succeed(None)
    for log_entry in reversed(log_json['log']):
      self.comparator.addRevision(log_entry['commit'])
      path = REVISION_DETAIL_TEMPLATE % (self.repo_path, log_entry['commit'])
      d.addCallback(lambda _: self.agent.request('GET', path, retry=5))
      def _report_error(result):
        log.err(result, '... while fetching %r from gitiles server.' % path)
      d.addCallback(self._create_change)
      d.addErrback(_report_error)
    return d

  def startService(self):
    path = LOG_TEMPLATE % (self.repo_path, self.branch, 1)
    d = self.agent.request('GET', path, retry=5)
    def _finish(log_json):
      self.last_head = log_json['log'][0]['commit']
      PollingChangeSource.startService(self)
    d.addCallback(_finish)

  def poll(self):
    d = self.lock.acquire()
    log_spec = '%s..%s' % (self.last_head, self.branch)
    path = LOG_TEMPLATE % (self.repo_path, log_spec, 100)
    d.addCallback(lambda _: self.agent.request('GET', path, retry=5))
    d.addCallback(self._process_log)
    d.addBoth(_always_unlock, self.lock)
    return d

  def describe(self):
    status = self.__class__.__name__
    if not self.master:
      status += ' [STOPPED - check log]'
    return '%s repo_url=%s' % (status, self.repo_url)
