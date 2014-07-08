# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import re

from twisted.internet import defer
from twisted.python import log

from buildbot.schedulers.base import BaseScheduler
from buildbot.status.base import StatusReceiverMultiService
from buildbot.status.builder import Results

from common.gerrit_agent import GerritAgent
from master.gerrit_poller import GerritPoller


class JobDefinition(object):
  """Describes a try job posted on Gerrit."""
  def __init__(self, builder_names=None):
    # Force str type and remove empty builder names.
    self.builder_names = [str(b) for b in (builder_names or []) if b]

  def __repr__(self):
    return repr(self.__dict__)

  @staticmethod
  def parse(text):
    """Parses a try job definition."""
    text = text and text.strip()
    if not text:
      # Return an empty definition.
      return JobDefinition()

    # Parse as json.
    try:
      job = json.loads(text)
    except:
      raise ValueError('Couldn\'t parse job definition: %s' % text)

    # Convert to canonical form.
    if isinstance(job, list):
      # Treat a list as builder name list.
      job = {'builderNames': job}
    elif not isinstance(job, dict):
      raise ValueError('Job definition must be a JSON object or array.')

    return JobDefinition(job.get('builderNames'))


class _TryJobGerritPoller(GerritPoller):
  """Polls issues, creates changes and calls scheduler.submitJob.

  This class is a part of TryJobGerritScheduler implementation and not designed
  to be used otherwise.
  """

  change_category = 'tryjob'

  MESSAGE_REGEX_TRYJOB = re.compile('^!tryjob(.*)$', re.I | re.M)

  def __init__(self, scheduler, gerrit_host, gerrit_projects=None,
               pollInterval=None, dry_run=None):
    assert scheduler
    GerritPoller.__init__(self, gerrit_host, gerrit_projects, pollInterval,
                          dry_run)
    self.scheduler = scheduler

  def _is_interesting_message(self, message):
    return self.MESSAGE_REGEX_TRYJOB.search(message['message'])

  def getChangeQuery(self):
    query = GerritPoller.getChangeQuery(self)
    # Request only issues with TryJob=+1 label.
    query += '+label:TryJob=%2B1'
    return query

  def parseJob(self, message):
    """Parses a JobDefinition from a Gerrit message."""
    tryjob_match = self.MESSAGE_REGEX_TRYJOB.search(message['message'])
    assert tryjob_match
    return JobDefinition.parse(tryjob_match.group(1))

  @defer.inlineCallbacks
  def addChange(self, change, message):
    """Parses a job, adds a change and calls self.scheduler.submitJob."""
    try:
      job = self.parseJob(message)
      revision = self.findRevisionShaForMessage(change, message)
      buildbot_change = yield self.addBuildbotChange(change, revision)
      yield self.scheduler.submitJob(buildbot_change, job)
      defer.returnValue(buildbot_change)
    except Exception as e:
      log.err('TryJobGerritPoller failed: %s' % e)
      raise


class TryJobGerritScheduler(BaseScheduler):
  """Polls try jobs on Gerrit and creates buildsets."""
  def __init__(self, name, default_builder_names, gerrit_host,
               gerrit_projects=None, pollInterval=None, dry_run=None):
    """Creates a new TryJobGerritScheduler.

    Args:
        name: name of the scheduler.
        default_builder_names: a list of builder names used in case a job didn't
            specify any.
        gerrit_host: URL to the Gerrit instance
        gerrit_projects: Gerrit projects to filter issues.
        pollInterval: frequency of polling.
    """
    BaseScheduler.__init__(self, name,
                           builderNames=default_builder_names,
                           properties={})
    self.poller = _TryJobGerritPoller(self, gerrit_host, gerrit_projects,
                                      pollInterval, dry_run)

  def setServiceParent(self, parent):
    BaseScheduler.setServiceParent(self, parent)
    self.poller.master = self.master
    self.poller.setServiceParent(self)

  def gotChange(self, *args, **kwargs):
    """Do nothing because changes are processed by submitJob."""

  @defer.inlineCallbacks
  def submitJob(self, change, job):
    bsid = yield self.addBuildsetForChanges(
        reason='tryjob',
        changeids=[change.number],
        builderNames=job.builder_names,
        properties=change.properties)
    log.msg('Successfully submitted a Gerrit try job for %s: %s.' %
            (change.who, job))
    defer.returnValue(bsid)


class TryJobGerritStatus(StatusReceiverMultiService):
  """Posts results of a try job back to a Gerrit change."""

  def __init__(self, gerrit_host, review_factory=None):
    """Creates a TryJobGerritStatus.

    Args:
      gerrit_host: a URL of the Gerrit instance.
      review_factory: a function (builder_name, build, result) => review,
        where review is a dict described in Gerrit docs:
        https://gerrit-review.googlesource.com/Documentation/rest-api-changes.html#review-input
    """
    StatusReceiverMultiService.__init__(self)
    self.review_factory = review_factory or self.createReview
    self.agent = GerritAgent(gerrit_host)
    self.status = None

  def createReview(self, builder_name, build, result):
    review = {}
    if result is not None:
      message = ('A try job has finished on builder %s: %s' %
                 (builder_name, Results[result].upper()))
    else:
      message = 'A try job has started on builder %s' % builder_name
      # Do not send email about this.
      review['notify'] = 'NONE'

    # Append build url.
    # A line break in a Gerrit message is \n\n.
    assert self.status
    build_url = self.status.getURLForThing(build)
    message = '%s\n\n%s' % (message, build_url)

    review['message'] = message
    return review

  def sendUpdate(self, builder_name, build, result):
    """Posts a message and labels, if any, on a Gerrit change."""
    props = build.properties
    change_id = (props.getProperty('event.change.id') or
                 props.getProperty('parent_event.change.id'))
    revision = props.getProperty('revision')
    if change_id and revision:
      review = self.review_factory(builder_name, build, result)
      if review:
        log.msg('Sending a revew for change %s: %s' % (change_id, review))
        path = '/changes/%s/revisions/%s/review' % (change_id, revision)
        return self.agent.request('POST', path, body=review)

  def startService(self):
    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

  def builderAdded(self, name, builder):
    # Subscribe to this builder.
    return self

  def buildStarted(self, builder_name, build):
    self.sendUpdate(builder_name, build, None)

  def buildFinished(self, builder_name, build, result):
    self.sendUpdate(builder_name, build, result)
