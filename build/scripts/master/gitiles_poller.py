# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Classes for polling a git repository via the gitiles web interface.

The advantage of using gitiles is that a local clone is not needed."""

import datetime
import json
import os
import re
import traceback
import urllib
from urlparse import urlparse

import sqlalchemy as sa
import buildbot.status.web.base as base
from buildbot.status.web.console import RevisionComparator
from buildbot.changes.base import PollingChangeSource
from twisted.internet import defer
from twisted.python import log

from common.gerrit_agent import GerritAgent


LOG_TEMPLATE = '%s/+log/%s?format=JSON&n=%d'
REFS_TEMPLATE = '%s/+refs?format=JSON'
REVISION_DETAIL_TEMPLATE = '%s/+/%s?format=JSON'


def time_to_datetime(tm):
  tm_parts = tm.split()
  # Time stamps from gitiles sometimes have a UTC offset (e.g., -0800), and
  # sometimes not.  time.strptime() cannot parse UTC offsets, so if one is
  # present, strip it out and parse manually.
  timezone = None
  if len(tm_parts) == 6:
    tm = ' '.join(tm_parts[:-1])
    timezone = tm_parts[-1]
  dt = datetime.datetime.strptime(tm, "%a %b %d %H:%M:%S %Y")
  if timezone:
    m = re.match(r'([+-])(\d\d):?(\d\d)?', timezone)
    assert m, 'Could not parse time zone information from "%s"' % timezone
    timezone_delta = datetime.timedelta(
        hours=int(m.group(2)), minutes=int(m.group(3) or '0'))
    if m.group(1) == '-':
      dt += timezone_delta
    else:
      dt -= timezone_delta
  return dt


class Revision(object):
  """Commit wrapper that can be compared to other commits through a comparator.

  (See GitilesRevisionComparator.comparableRevision)
  """
  def __init__(self, comparator, commit):
    self.comparator = comparator
    self.commit = commit

  def __cmp__(self, other):
    assert self.comparator.initialized, "The comparator must be initialized"
    return self.comparator.tagcmp(self.commit, other.commit)

  def __repr__(self):
    return self.commit


class GitilesRevisionComparator(RevisionComparator):
  """Tracks the commit order of tags in a git repository."""

  def __init__(self):
    super(GitilesRevisionComparator, self).__init__()
    self.sha1_lookup = {}
    self.initialized = False
    self.initLock = defer.DeferredLock()

  @defer.inlineCallbacks
  def initialize(self, db):
    yield self.initLock.acquire()
    if self.initialized:
      self.initLock.release()
      return
    def db_thread_main(conn):
      changes_tbl = db.model.changes
      q = changes_tbl.select(order_by=[sa.asc(changes_tbl.c.changeid)])
      rp = conn.execute(q)
      for row in rp:
        self.addRevision(row.revision)
    try:
      yield db.pool.do(db_thread_main)
      log.msg(
          'GitilesRevisionComparator: Finished initializing revision history')
      self.initialized = True
    finally:
      self.initLock.release()

  def comparableRevision(self, commit):
    assert self.initialized, "The comparator must be initialized"
    return Revision(self, commit)

  def addRevision(self, revision):
    if revision in self.sha1_lookup:
      return
    idx = len(self.sha1_lookup)
    self.sha1_lookup[revision] = idx

  def tagcmp(self, x, y):
    return cmp(self.sha1_lookup[x], self.sha1_lookup[y])

  def isValidRevision(self, revision):
    return revision in self.sha1_lookup

  def isRevisionEarlier(self, first_change, second_change):
    return self.tagcmp(first_change.revision, second_change.revision) < 0

  def getSortingKey(self):
    return lambda c: self.sha1_lookup.__getitem__(c.revision)


class GitilesPoller(PollingChangeSource):
  """Polls a git repository using the gitiles web interface. """

  git_svn_id_re = re.compile('^git-svn-id: (.*)@([0-9]+) [0-9a-fA-F\-]*$')
  re_pattern_type = type(re.compile(''))

  def __init__(
      self, repo_url, branches=None, pollInterval=30, category=None,
      project=None, revlinktmpl=None, agent=None, svn_mode=False,
      svn_branch=None, change_filter=None, comparator=None):
    """Args:

    repo_url: URL of the gitiles service to be polled.
    branches: List of strings and/or compiled regular expressions, specifying
        the branches to be polled.
    pollInterval: Number of seconds between polling operations.
    category: Category to be applied to generated Change objects.
    project: Project to be applied to generated Change objects.
    revlinktmpl: String template, taking a single 'revision' parameter, used to
        generate a web link to a revision.
    agent: A GerritAgent object used to make requests to the gitiles service.
    svn_mode: When polling a mirror of an svn repository, create changes using
        the svn revision number.
    svn_branch: When svn_mode=True, this is used to determine the svn branch
        name for each change.  It can be either a static string, or a function
        that takes (gitiles_commit_json, git_branch) as arguments and returns
        a static string.
    comparator: A GitilesRevisionComparator object, or None.  This is used to
        share a single comparator between multiple pollers.
    """
    u = urlparse(repo_url)
    self.repo_url = repo_url
    self.repo_host = u.netloc
    self.repo_path = urllib.quote(u.path)
    if branches is None:
      branches = ['master']
    elif isinstance(branches, basestring):
      branches = [branches]
    self.branches = []
    for b in branches:
      if not isinstance(b, self.re_pattern_type):
        b = b.lstrip('/')
        if not b.startswith('refs/'):
          b = 'refs/heads/' + b
      self.branches.append(b)
    self.branch_heads = {}
    self.pollInterval = pollInterval
    self.category = category
    if project is None:
      project = os.path.basename(repo_url)
      if project.endswith('.git'):
        project = project[:-4]
    self.project = project
    self.revlinktmpl = revlinktmpl or '%s/+/%%s' % repo_url
    self.svn_mode = svn_mode
    self.svn_branch = svn_branch
    if svn_mode and not svn_branch:
      self.svn_branch = project
    if agent is None:
      agent = GerritAgent('%s://%s' % (u.scheme, u.netloc), read_only=True)
    self.agent = agent
    self.dry_run = os.environ.get('POLLER_DRY_RUN')
    self.change_filter = change_filter
    self.comparator = comparator or GitilesRevisionComparator()

  @defer.inlineCallbacks
  def startService(self):
    # Initialize revision comparator with revisions from all changes
    # known to buildbot.
    yield self.comparator.initialize(self.master.db)

    # Get the head commit for each branch being polled.
    branches = yield self._get_branches()
    for branch, branch_head in branches.iteritems():
      log.msg('GitilesPoller: Initial revision for branch %s is %s' % (
          branch, branch_head))
      self.branch_heads[branch] = branch_head

    PollingChangeSource.startService(self)

  @defer.inlineCallbacks
  def _get_branches(self):
    result = {}
    path = REFS_TEMPLATE % (self.repo_path,)
    if self.dry_run:
      refs_json = {}
    else:
      refs_json = yield self.agent.request('GET', path, retry=5)
    for ref, ref_head in refs_json.iteritems():
      for branch in self.branches:
        if (ref == branch or
            (isinstance(branch, self.re_pattern_type) and
             (branch.match(ref) or
              (ref.startswith('refs/heads/') and branch.match(ref[11:]))))):
          result[ref] = ref_head['value']
          break
    deleted_branches = []
    for branch in self.branch_heads:
      if branch not in result:
        deleted_branches.append(branch)
    for branch in deleted_branches:
      log.msg('GitilesPoller: Deleting branch head for %s' % (branch,))
      del self.branch_heads[branch]
    defer.returnValue(result)

  def _create_change(self, commit_json, branch):
    """Send a new Change object to the buildbot master."""
    if not commit_json:
      return
    if self.change_filter and not self.change_filter(commit_json, branch):
      return
    commit_branch = branch.rpartition('/')[2]
    if callable(self.svn_branch):
      commit_branch = self.svn_branch(commit_json, branch)
    elif self.svn_branch:
      commit_branch = self.svn_branch
    commit_author = commit_json['author']['email']
    commit_tm = time_to_datetime(commit_json['committer']['time'])
    commit_files = []
    if 'tree_diff' in commit_json:
      commit_files = [
          x['new_path'] for x in commit_json['tree_diff'] if 'new_path' in x]
    commit_msg = commit_json['message']
    repo_url = self.repo_url
    revision = commit_json['commit']
    properties = { 'git_revision': revision }
    if self.svn_mode:
      revision = None
      for line in reversed(commit_msg.splitlines()):
        m = self.git_svn_id_re.match(line)
        if m:
          repo_url = m.group(1)
          revision = m.group(2)
          break
      if revision is None:
        log.err(
            'GitilesPoller: Could not parse svn revision out of commit message '
            'for commit %s in %s' % (commit_json['commit'], self.repo_url))
        return None
      self.comparator.addRevision(revision)
    revlink = ''
    if self.revlinktmpl and revision:
      revlink = self.revlinktmpl % revision
    return self.master.addChange(
        author=commit_author,
        revision=revision,
        files=commit_files,
        comments=commit_msg,
        when_timestamp=commit_tm,
        branch=commit_branch,
        category=self.category,
        project=self.project,
        properties=properties,
        repository=repo_url,
        revlink=revlink)

  @defer.inlineCallbacks
  def _fetch_new_commits(self, branch, since):
    """Query gitiles for all commits on 'branch' more recent than 'since'."""
    result = []
    log_json = {'next': branch}
    while 'next' in log_json:
      log_spec = '%s..%s' % (since, log_json['next'])
      path = LOG_TEMPLATE % (self.repo_path, log_spec, 100)
      if self.dry_run:
        log_json = {}
      else:
        log_json = yield self.agent.request('GET', path, retry=5)
      if log_json.get('log'):
        result.extend(log_json['log'])
    result.reverse()
    defer.returnValue(result)

  @staticmethod
  def _collate_commits(a, b):
    """Shuffle together two lists of commits.

    The result will be sorted by commit time, while guaranteeing that there are
    no inversions compared to the argument lists."""
    a = [(c, time_to_datetime(c[0]['committer']['time'])) for c in a]
    b = [(c, time_to_datetime(c[0]['committer']['time'])) for c in b]
    result = []
    while a and b:
      if a[-1][1] > b[-1][1]:
        result.append(a.pop()[0])
      else:
        result.append(b.pop()[0])
    while a:
      result.append(a.pop()[0])
    while b:
      result.append(b.pop()[0])
    result.reverse()
    return result

  @defer.inlineCallbacks
  def poll(self):
    all_commits = []
    branches = yield self._get_branches()
    for branch, branch_head in branches.iteritems():
      try:
        branch_commits = None
        if branch not in self.branch_heads:
          # New branch: trigger a build based on the current head.
          log.msg('GitilesPoller: Discovered new branch %s.' % branch)
          branch_commits = yield self._fetch_new_commits(
              branch, branch + '~')
        elif self.branch_heads[branch] != branch_head:
          branch_commits = yield self._fetch_new_commits(
              branch, self.branch_heads[branch])
        if branch_commits:
          self.branch_heads[branch] = branch_commits[-1]['commit']
          branch_commits = [(c, branch) for c in branch_commits]
          all_commits = self._collate_commits(all_commits, branch_commits)
      except Exception:
        msg = ('GitilesPoller: Error while fetching logs for branch %s:\n%s' %
                   (branch, traceback.format_exc()))
        log.err(msg)
    for commit in all_commits:
      commit, branch = commit
      if not self.svn_mode:
        self.comparator.addRevision(commit['commit'])
      try:
        path = REVISION_DETAIL_TEMPLATE % (self.repo_path, commit['commit'])
        if not self.dry_run:
          detail = yield self.agent.request('GET', path, retry=5)
          yield self._create_change(detail, branch)
      except Exception:
        msg = ('GitilesPoller: Error while processing revision %s '
               'on branch %s:\n%s' % (
                   commit['commit'], branch, traceback.format_exc()))
        log.err(msg)
    else:
      log.msg('GitilesPoller: No new commits.')

  def describe(self):
    status = self.__class__.__name__
    if not self.master:
      status += ' [STOPPED - check log]'
    return '%s repo_url=%s' % (status, self.repo_url)


class GitilesStatus(base.HtmlResource):
  """This provides, in JSON, data about the specified GitilesPoller."""
  contentType = "application/json"

  def __init__(self, poller):
    self.poller = poller
    super(GitilesStatus, self).__init__()

  def content(self, request, ctx):
    data = {
        'branch_heads': self.poller.branch_heads,
    }
    return json.dumps(data)
