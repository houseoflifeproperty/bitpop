# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import logging
import os
import urllib

from buildbot.changes import base
from buildbot.util import deferredLocked
from twisted.python import log
from twisted.internet import defer

from common.gerrit_agent import GerritAgent

class GerritPoller(base.PollingChangeSource):
  """A poller which queries a gerrit server for new changes and patchsets."""

  # TODO(szager): Due to the way query continuation works in gerrit (using
  # the 'S=%d' URL parameter), there are two distinct error scenarios that
  # are currently unhandled:
  #
  #   - A new patch set is uploaded.
  #   - When the poller runs, the change is #11, meaning it doesn't come in
  #     the first batch of query results.
  #   - In between the first and second queries, another patch set is
  #     uploaded to the same change, bumping the change up to #1 in the list.
  #   - The second query skips ahead by 10, and never sees the change.
  #
  #   - A new patch set is uploaded.
  #   - When the poller runs, the change is #10, and appears in the first set
  #     of query results.
  #   - In between the first and second queries, some other change gets a new
  #     patch set and moves up to #1, bumping the current #10 to #11.
  #   - The second query skips 10, getting changes 11-20.  So, the change that
  #     was already processes is processed again.
  #
  # Both of these problems need the same solution: keep some state in poller of
  # 'patch sets already processed'; and relax the 'since' parameter to
  # processChanges so that it goes further back in time than the last polling
  # event (maybe pollInterval*3).

  change_category = 'patchset-created'

  def __init__(self, gerrit_host, gerrit_projects=None, pollInterval=None,
               dry_run=None):
    """Constructs a new Gerrit poller.

    Args:
      gerrit_host: (str or GerritAgent) If supplied as a GerritAgent, the
          Gerrit Agent to use when polling; otherwise, the host parameter to
          use to construct the GerritAgent to poll through.
      gerrit_projects: (list) A list of project names (str) to poll.
      pollInterval: (int or datetime.timedelta) The amount of time to wait in
          between polls.
      dry_run: (bool) If 'True', then polls will not actually be executed.
    """
    if isinstance(pollInterval, datetime.timedelta):
      pollInterval = pollInterval.total_seconds()
    if isinstance(gerrit_projects, basestring):
      gerrit_projects = [gerrit_projects]
    self.gerrit_projects = gerrit_projects
    if pollInterval:
      self.pollInterval = pollInterval
    self.initLock = defer.DeferredLock()
    self.last_timestamp = None

    if dry_run is None:
      dry_run = 'POLLER_DRY_RUN' in os.environ
    self.dry_run = dry_run

    self.agent = gerrit_host
    if not isinstance(self.agent, GerritAgent):
      self.agent = GerritAgent(self.agent)

  @staticmethod
  def _parse_timestamp(tm):
    tm = tm[:tm.index('.')+7]
    try:
      return datetime.datetime.strptime(tm, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
      return datetime.datetime.strptime(tm, '%Y-%m-%d %H:%M:%S')

  def startService(self):
    if not self.dry_run:
      self.initLastTimeStamp()
    base.PollingChangeSource.startService(self)

  @staticmethod
  def buildQuery(terms, operator=None):
    """Builds a Gerrit query from terms.

    This function will go away once the new GerritAgent lands.
    """
    connective = ('+%s+' % operator) if operator else '+'
    terms_with_parens = [('(%s)' % t) if ('+' in t) else t
                         for t in terms]
    return connective.join(terms_with_parens)

  def getChangeQuery(self):  # pylint: disable=R0201
    # Fetch only open issues.
    terms = ['status:open']

    # Filter by projects.
    if self.gerrit_projects:
      project_terms = ['project:%s' % urllib.quote(p, safe='')
                       for p in self.gerrit_projects]
      terms.append(self.buildQuery(project_terms, 'OR'))

    return self.buildQuery(terms)

  def request(self, path, method='GET'):
    log.msg('Gerrit request: %s' % path, logLevel=logging.DEBUG)
    return self.agent.request(method, path)

  @deferredLocked('initLock')
  def initLastTimeStamp(self):
    log.msg('GerritPoller: Getting latest timestamp from gerrit server.')
    query = self.getChangeQuery()
    path = '/changes/?q=%s&n=1' % query
    d = self.request(path)
    def _get_timestamp(j):
      if len(j) == 0:
        self.last_timestamp = datetime.datetime.now()
      else:
        self.last_timestamp = self._parse_timestamp(j[0]['updated'])
    d.addCallback(_get_timestamp)
    return d

  def getChanges(self, skip=None):
    path = '/changes/?q=%s&n=10' % self.getChangeQuery()
    if skip:
      path += '&S=%d' % skip
    return self.request(path)

  def _is_interesting_message(self, message):  # pylint: disable=R0201
    return message['message'].startswith('Uploaded patch set ')

  def checkForNewPatchset(self, change, since):
    o_params = '&'.join('o=%s' % x for x in (
        'MESSAGES', 'ALL_REVISIONS', 'ALL_COMMITS', 'ALL_FILES'))
    path = '/changes/%s?%s' % (change['_number'], o_params)
    d = self.request(path)
    def _parse_messages(j):
      if not j or 'messages' not in j:
        return
      for m in reversed(j['messages']):
        if self._parse_timestamp(m['date']) <= since:
          break
        if self._is_interesting_message(m):
          return j, m
    d.addCallback(_parse_messages)
    return d

  def getChangeUrl(self, change):
    """Generates a URL for a Gerrit change."""
    # GerritAgent stores its URL as protocol and host.
    return '%s/#/c/%s' % (self.agent.base_url,
                          change['_number'])

  def getRepositoryUrl(self, change):
    """Generates a URL for a Gerrit repository containing a change"""
    return '%s/%s' % (self.agent.base_url,
                      change['project'])

  def addBuildbotChange(self, change, revision=None):
    """Adds a buildbot change into the database.

    Args:
      change: ChangeInfo Gerrit object. Documentation:
        https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#change-info
      revision: the sha of the buildbot change revision to use. Defaults to the
        value of change['current_revision']

    Returns the new buildbot change as Deferred.
    """
    revision = revision or change['current_revision']
    revision_details = change['revisions'][revision]
    commit = revision_details['commit']

    properties = {
        'event.change.number': change['_number'],
        'event.change.id': change['id'],
        'event.change.url': self.getChangeUrl(change),
    }
    if change['status'] == 'NEW':
      ref = revision_details.get('fetch', {}).get('http', {}).get('ref')
      if ref:
        properties['event.patchSet.ref'] = ref
    elif change['status'] in ('SUBMITTED', 'MERGED'):
      properties['event.refUpdate.newRev'] = revision
    chdict = {
        'author': '%s <%s>' % (
            commit['author']['name'], commit['author']['email']),
        'project': change['project'],
        'branch': change['branch'],
        'revision': revision,
        'comments': commit['subject'],
        'files': revision_details.get('files', {'UNKNOWN': None}).keys(),
        'category': self.change_category,
        'when_timestamp': self._parse_timestamp(commit['committer']['date']),
        'revlink': self.getChangeUrl(change),
        'repository': self.getRepositoryUrl(change),
        'properties': properties,
    }
    d = self.master.addChange(**chdict)
    d.addErrback(log.err, 'GerritPoller: Could not add buildbot change for '
                 'gerrit change %s.' % revision_details['_number'])
    return d

  @staticmethod
  def findRevisionShaForMessage(change, message):
    def warn(text):
      log.msg('GerritPoller warning: %s. Change: %s, message: %s' %
              (text, change['id'], message['message']))

    revision_number = message.get('_revision_number')
    if revision_number is None:
      warn('A message doesn\'t have a _revision_number')
      return None
    for sha, revision in change['revisions'].iteritems():
      if revision['_number'] == revision_number:
        return sha
    warn('a revision wasn\'t found for message')

  def addChange(self, change, message):
    revision = self.findRevisionShaForMessage(change, message)
    return self.addBuildbotChange(change, revision)

  def processChanges(self, j, since, skip=0):
    need_more = bool(j)
    for change in j:
      skip += 1
      tm = self._parse_timestamp(change['updated'])
      if tm <= since:
        need_more = False
        break
      if self.gerrit_projects and change['project'] not in self.gerrit_projects:
        continue
      d = self.checkForNewPatchset(change, since)
      d.addCallback(lambda x: self.addChange(*x) if x else None)
    if need_more and j[-1].get('_more_changes'):
      d = self.getChanges(skip=skip)
      d.addCallback(self.processChanges, since=since, skip=skip)
    else:
      d = defer.succeed(None)
    return d

  @deferredLocked('initLock')
  def poll(self):
    if self.dry_run:
      return

    log.msg('GerritPoller: getting latest changes...')
    since = self.last_timestamp
    d = self.getChanges()
    def _update_last_timestamp(j):
      if j:
        self.last_timestamp = self._parse_timestamp(j[0]['updated'])
      return j
    d.addCallback(_update_last_timestamp)
    d.addCallback(self.processChanges, since=since)
    return d
