# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
import os
import time
import urllib
import urlparse

from buildbot.changes import base
from buildbot.schedulers.trysched import BadJobfile
from buildbot.status.builder import EXCEPTION
from twisted.application import internet
from twisted.internet import defer
from twisted.python import log
from twisted.web import client

from master import master_utils
from master.try_job_base import TryJobBase


class _ValidUserPoller(internet.TimerService):
  """Check chromium-access for users allowed to send jobs from Rietveld.
  """
  # The name of the file that contains the password for authenticating
  # requests to chromium-access.
  _PWD_FILE = '.try_job_rietveld_password'
  _NORMAL_DOMAIN = '@chromium.org'
  _SPECIAL_DOMAIN = '@google.com'

  def __init__(self, interval):
    """
    Args:
      interval: Interval used to poll chromium-access, in seconds.
    """
    if interval:
      internet.TimerService.__init__(self, interval, _ValidUserPoller._poll,
                                     self)
    self._users = frozenset()

  def contains(self, email):
    """Checks if the given email address is a valid user.

    Args:
      email: The email address to check against the internal list.

    Returns:
      True if the email address is allowed to send try jobs from rietveld.
    """
    if email is None:
      return False
    return email in self._users or email.endswith(self._SPECIAL_DOMAIN)

  # base.PollingChangeSource overrides:
  def _poll(self):
    """Polls for valid user names.

    Returns:
      A deferred objects to be called once the operation completes.
    """
    log.msg('ValidUserPoller._poll')
    d = defer.succeed(None)
    d.addCallback(self._GetUsers)
    d.addCallback(self._MakeSet)
    d.addErrback(log.err, 'error in ValidUserPoller')
    return d

  def _GetUsers(self, _):
    """Downloads list of valid users.

    Returns:
      A string of lines containing the email addresses of users allowed to
      send jobs from Rietveld.
    """
    if not os.path.isfile(self._PWD_FILE):
      log.msg("No password file '%s'; no valid users." % self._PWD_FILE)
      return ""

    pwd = open(self._PWD_FILE).readline().strip()
    now_string = str(int(time.time()))
    params = {
      'md5': hashlib.md5(pwd + now_string).hexdigest(),
      'time': now_string
    }

    return client.getPage('https://chromium-access.appspot.com/auto/all_users',
                          agent='buildbot',
                          method='POST',
                          postdata=urllib.urlencode(params))

  def _MakeSet(self, data):
    """Converts the input data string into a set of email addresses.
    """
    emails = (email.strip() for email in data.splitlines())
    self._users = frozenset(email for email in emails if email)
    log.msg('Found %d users' % len(self._users))


class _RietveldPoller(base.PollingChangeSource):
  """Polls Rietveld for any pending patch sets to build.

  Periodically polls Rietveld to see if any patch sets have been marked by
  users to be tried.  If so, send them to the trybots.
  """

  def __init__(self, get_pending_endpoint, interval, cachepath=None):
    """
    Args:
      get_pending_endpoint: Rietveld URL string used to retrieve jobs to try.
      interval: Interval used to poll Rietveld, in seconds.
      cachepath: Path to file where state to persist between master restarts
                 will be stored.
    """
    # Set interval time in base class.
    self.pollInterval = interval

    # A string URL for the Rietveld endpoint to query for pending try jobs.
    self._get_pending_endpoint = get_pending_endpoint

    # Cursor used to keep track of next patchset(s) to try.  If the cursor
    # is None, then try from the beginning.
    self._cursor = None

    # Try job parent of this poller.
    self._try_job_rietveld = None

    self._cachepath = cachepath

    if self._cachepath:
      if os.path.exists(self._cachepath):
        with open(self._cachepath) as f:
          # Using JSON allows us to be flexible and extend the format
          # in a compatible way.
          data = json.load(f)
          self._cursor = data.get('cursor').encode('utf-8')

  # base.PollingChangeSource overrides:
  def poll(self):
    """Polls Rietveld for any pending try jobs and submit them.

    Returns:
      A deferred objects to be called once the operation completes.
    """
    log.msg('RietveldPoller.poll')
    d = defer.succeed(None)
    d.addCallback(self._OpenUrl)
    d.addCallback(self._ParseJson)
    d.addErrback(log.err, 'error in RietveldPoller')  # eat errors
    return d

  def setServiceParent(self, parent):
    base.PollingChangeSource.setServiceParent(self, parent)
    self._try_job_rietveld = parent

  def _OpenUrl(self, _):
    """Downloads pending patch sets from Rietveld.

    Returns: A string containing the pending patchsets from Rietveld
        encoded as JSON.
    """
    endpoint = self._get_pending_endpoint
    if self._cursor:
      sep = '&' if '?' in endpoint else '?'
      endpoint = endpoint + '%scursor=%s' % (sep, self._cursor)

    log.msg('RietveldPoller._OpenUrl: %s' % endpoint)
    return client.getPage(endpoint, agent='buildbot', timeout=2*60)

  def _ParseJson(self, json_string):
    """Parses the JSON pending patch set information.

    Args:
      json_string: A string containing the serialized JSON jobs.

    Returns: A list of pending try jobs.  This is the list of all jobs returned
        by Rietveld, not simply the ones we tried this time.
    """
    data = json.loads(json_string)
    d = self._try_job_rietveld.SubmitJobs(data['jobs'])
    def success_callback(value):
      self._cursor = str(data['cursor'])
      self._try_job_rietveld.processed_keys.clear()

      if self._cachepath:
        with open(self._cachepath, 'w') as f:
          json.dump({'cursor': self._cursor}, f)

      return value
    d.addCallback(success_callback)
    return d


class TryJobRietveld(TryJobBase):
  """A try job source that gets jobs from pending Rietveld patch sets."""

  def __init__(self, name, pools, properties=None, last_good_urls=None,
               code_review_sites=None, project=None, filter_master=False,
               cachepath=None):
    """Creates a try job source for Rietveld patch sets.

    Args:
      name: Name of this scheduler.
      pools: No idea.
      properties: Extra build properties specific to this scheduler.
      last_good_urls: Dictionary of project to last known good build URL.
      code_review_sites: Dictionary of project to code review site.  This
          class care only about the 'chrome' project.
      project: The name of the project whose review site URL to extract.
          If the project is not found in the dictionary, an exception is
          raised.
      filter_master: Filter try jobs by master name. Necessary if several try
          masters share the same rietveld instance.
    """
    TryJobBase.__init__(self, name, pools, properties,
                        last_good_urls, code_review_sites)
    endpoint = self._GetRietveldEndPointForProject(
        code_review_sites, project, filter_master)

    self._poller = _RietveldPoller(endpoint, interval=10, cachepath=cachepath)
    self._valid_users = _ValidUserPoller(interval=12 * 60 * 60)
    self._project = project

    # Cleared by _RietveldPoller._ParseJson's success callback.
    self.processed_keys = set()

    log.msg('TryJobRietveld created, get_pending_endpoint=%s '
            'project=%s' % (endpoint, project))

  @staticmethod
  def _GetRietveldEndPointForProject(code_review_sites, project,
                                     filter_master):
    """Determines the correct endpoint for the chrome review site URL.

    Args:
      code_review_sites: Dictionary of project name to review site URL.
      project: The name of the project whose review site URL to extract.
          If the project is not found in the dictionary, an exception is
          raised.
      filter_master: Filter try jobs by master name. Necessary if several try
          masters share the same rietveld instance.

    Returns: A string with the endpoint extracted from the chrome
        review site URL, which is the URL to poll for new patch
        sets to try.
    """
    if project not in code_review_sites:
      raise Exception('No review site for "%s"' % project)

    url = 'get_pending_try_patchsets?limit=100'

    # Filter by master name if specified.
    if filter_master:
      url += '&master=%s' % urllib.quote_plus(master_utils.GetMastername())

    return urlparse.urljoin(code_review_sites[project], url)

  @defer.inlineCallbacks
  def SubmitJobs(self, jobs):
    """Submit pending try jobs to slaves for building.

    Args:
      jobs: a list of jobs.  Each job is a dictionary of properties describing
          what to build.
    """
    log.msg('TryJobRietveld.SubmitJobs: %s' % json.dumps(jobs, indent=2))
    for job in jobs:
      try:
        # Gate the try job on the user that requested the job, not the one that
        # authored the CL.
        if not self._valid_users.contains(job['requester']):
          raise BadJobfile(
              'TryJobRietveld rejecting job from %s' % job['requester'])

        if job['key'] in self.processed_keys:
          log.msg('TryJobRietveld skipping processed key %s' % job['key'])
          continue

        if job['email'] != job['requester']:
          # Note the fact the try job was requested by someone else in the
          # 'reason'.
          job['reason'] = job.get('reason') or ''
          if job['reason']:
            job['reason'] += '; '
          job['reason'] += "This CL was triggered by %s" % job['requester']

        options = {
            'bot': {job['builder']: job['tests']},
            'email': [job['email']],
            'project': [self._project],
            'try_job_key': job['key'],
        }
        # Transform some properties as is expected by parse_options().
        for key in (
            'name', 'user', 'root', 'reason', 'clobber', 'patchset', 'issue',
            'requester', 'revision'):
          options[key] = [job[key]]

        # Now cleanup the job dictionary and submit it.
        cleaned_job = self.parse_options(options)

        yield self.get_lkgr(cleaned_job)
        c = yield self.master.addChange(
            author=','.join(cleaned_job['email']),
            # TODO(maruel): Get patchset properties to get the list of files.
            # files=[],
            revision=cleaned_job['revision'],
            comments='')
        changeids = [c.number]

        cleaned_job['patch_storage'] = 'rietveld'
        yield self.SubmitJob(cleaned_job, changeids)

        self.processed_keys.add(job['key'])
      except BadJobfile, e:
        # We need to mark it as failed otherwise it'll stay in the pending
        # state. Simulate a buildFinished event on the build.
        log.err('Got "%s" for issue %s' % (e, job.get('issue')))
        for service in self.master.services:
          if service.__class__.__name__ == 'TryServerHttpStatusPush':
            build = {
              'properties': [
                ('buildername', job.get('builder'), None),
                ('buildnumber', -1, None),
                ('issue', job['issue'], None),
                ('patchset', job['patchset'], None),
                ('project', self._project, None),
                ('revision', '', None),
                ('slavename', '', None),
                ('try_job_key', job['key'], None),
              ],
              'reason': job.get('reason', ''),
              # Use EXCEPTION until SKIPPED results in a non-green try job
              # results on Rietveld.
              'results': EXCEPTION,
            }
            service.push('buildFinished', build=build)
            self.processed_keys.add(job['key'])
            log.err('Rietveld updated')
            break
        else:
          self.processed_keys.add(job['key'])
          log.err('Rietveld not updated: no corresponding service found.')

  # TryJobBase overrides:
  def setServiceParent(self, parent):
    TryJobBase.setServiceParent(self, parent)
    self._poller.setServiceParent(self)
    self._poller.master = self.master
    self._valid_users.setServiceParent(self)
