# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import urllib

from buildbot.changes.base import PollingChangeSource
from buildbot.process.properties import Properties
from buildbot.schedulers.trysched import TryBase
from twisted.internet import defer
from twisted.python import log
from twisted.web import client

from master import get_password as get_pw


_DEFAULT_POLLING_INTERVAL = 10  # seconds


class JsonPoller(PollingChangeSource):
  """Polls a url for JSON blobs."""

  def __init__(self, url, password=None, interval=_DEFAULT_POLLING_INTERVAL):
    """
    Args:
      url: Url used to retrieve json blobs describing jobs.
      password: The password to use to authenticate to the url.
      interval: Interval used to poll the url, in seconds.
    """
    # Set the interval used by base PollingChangeSource
    self.pollInterval = interval

    # The url that the poller will poll.
    self._url = url.rstrip('/') + '/pull'
    self._password = password

    # The parent scheduler that is using this poller.
    self._scheduler = None

  def setServiceParent(self, parent):
    PollingChangeSource.setServiceParent(self, parent)
    self._scheduler = parent

  def poll(self):
    """Polls the url for any job JSON blobs and submits them.

    Override of PollingChangeSource base method.
    Returns:
      A deferred object to be called once the polling completes.
    """
    log.msg('JsonPoller.poll')
    if self._password:
      postdata = urllib.urlencode({'password': self._password})
    else:
      postdata = ''
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    d = client.getPage(self._url, method='POST',
                       postdata=postdata, headers=headers)
    d.addCallback(self._handleJobs)
    d.addErrback(log.err, 'error in JsonPoller.poll')
    return d

  def _handleJobs(self, blob):
    log.msg('JsonScheduler handling blob: %s' % blob)
    if not blob:
      return
    jobs = json.loads(blob)
    return self._scheduler.submitJobs(jobs)


class JsonScheduler(TryBase):
  """A scheduler to spawn jobs based on JSON blobs retrieved from a url."""

  compare_attrs = TryBase.compare_attrs + ('url',)

  def __init__(self, name, builders, url, properties=None):
    """
    Args:
      name: The name of this scheduler, for buildbot indexing.
      builders: The names of the builders it can schedule jobs for.
      url: The url to poll for new jobs.
      properties: Key-value pairs to be added to every job description.
    """
    TryBase.__init__(self, name, builders, properties or {})

    # The password to use for authentication.
    self._password = get_pw.Password('.jobqueue_password').MaybeGetPassword()

    # The poller instance that will be sending us jobs.
    self._poller = JsonPoller(url, self._password,
                              interval=_DEFAULT_POLLING_INTERVAL)

    # The url to which the scheduler posts that it started the job.
    self._url = url.rstrip('/') + '/accept/%s'

  def gotChange(self, _change, _important):  # pylint: disable=R0201
    log.msg('ERROR: gotChange was unexpectedly called.')

  def submitJobs(self, jobs):
    return defer.DeferredList([self.submitJob(job) for job in jobs])

  @defer.inlineCallbacks
  def submitJob(self, job):
    try:
      cid = yield self._createChange(job)
      log.msg('JsonScheduler added change: %s' % cid.number)
      ssid = yield self._createSourcestamp(cid.number, job)
      log.msg('JsonScheduler added sourcestamp %s' % ssid)
      bsid = yield self._createBuildset(ssid, job)
      log.msg('JsonScheduler added buildset %s' % bsid[0])
      yield self._acceptJob(bsid[0], job)
      log.msg('JsonScheduler accepted job %s' % job['job_key'])
    except Exception as e:
      log.err('JsonScheduler failed: %s' % e)


  def _createChange(self, job):
    return self.master.addChange(
        author=','.join(job.get('blamelist', [])),
        revision=job.get('revision', ''),
        comments='')

  def _createSourcestamp(self, cid, job):
    return self.master.db.sourcestamps.addSourceStamp(
        project=job.get('project', ''),
        repository=job.get('repository', ''),
        branch=job.get('branch', ''),
        revision=job.get('revision', ''))

  def _createBuildset(self, ssid, job):
    properties = Properties()
    properties.update(job, 'Job JSON')
    builderNames = self.filterBuilderList([job.get('buildername', None)])
    if not builderNames:
      log.msg("Job did not specify any allowed builder names")
      return defer.succeed(None)
    return self.addBuildsetForSourceStamp(
        ssid,
        builderNames=builderNames,
        reason=job.get('reason', 'Job from JsonScheduler'),
        properties=properties)

  def _acceptJob(self, bsid, job):
    if self._password:
      postdata = urllib.urlencode({'password': self._password})
    else:
      postdata = ''
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    # We are guaranteed job_key is a str, but json makes it unicode.
    return client.getPage(self._url % str(job['job_key']), method='POST',
                          postdata=postdata, headers=headers)

  def setServiceParent(self, parent):
    TryBase.setServiceParent(self, parent)
    self._poller.setServiceParent(self)
