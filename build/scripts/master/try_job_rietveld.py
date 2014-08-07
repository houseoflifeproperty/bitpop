# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import hashlib
import json
import os
import pytz
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


# Number of recent buildsets used to initialize RietveldPollerWithCache's cache.
MAX_RECENT_BUILDSETS_TO_INIT_CACHE = 10000


def str_to_datetime(text):
  try:
    return datetime.datetime.strptime(text, '%Y-%m-%d %H:%M:%S.%f')
  except ValueError:
    return datetime.datetime.strptime(text, '%Y-%m-%d %H:%M:%S')


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
    self._valid = False

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

  def valid(self):
    """Returns true if the poller has retrieved valid users successfully."""
    return self._valid

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
    self._valid = True


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


class _RietveldPollerWithCache(base.PollingChangeSource):
  """Polls Rietveld for any pending patch sets to build.

  Periodically polls Rietveld to see if any patch sets have been marked by
  users to be tried. If so, send them to the trybots. Uses cursor to download
  all pages within a single poll. To avoid sending same jobs, keeps a cache of
  the jobs that were already processed thus reducing chances of a duplicate job
  submission and increasing robustness to bugs in Rietveld. On the first poll
  this cache is initialized with jobs currently pending on the Buildbot.
  """

  def __init__(self, pending_jobs_url, interval, timeout=2*60):
    """
    Args:
      pending_jobs_url: Rietveld URL string used to retrieve jobs to try.
      interval: Interval used to poll Rietveld, in seconds.
    """
    self.pollInterval = interval
    self._try_job_rietveld = None
    self._pending_jobs_url = pending_jobs_url
    self._processed_keys = None
    self.timeout = timeout

  def getPage(self, url):  # pylint: disable=R0201
    """Schedules a page at `url` to be downloaded. Returns a deferred."""
    return client.getPage(url, agent='buildbot', timeout=self.timeout)

  # base.PollingChangeSource overrides:
  def poll(self):
    """Polls Rietveld for any pending try jobs and submit them.

    Returns:
      A deferred object to be called once the operation completes.
    """

    # Make sure setServiceParent was called before this method is called.
    assert self._try_job_rietveld

    # Check if we have valid user list, otherwise - do not submit any jobs. This
    # is different from having no valid users in the list, in which case
    # SubmitJobs will correctly discard the jobs.
    if not self._try_job_rietveld.has_valid_user_list():
      log.msg('[RPWC] No valid user list. Ignoring the poll request.')
      return

    log.msg('[RPWC] Poll started')
    log.msg('[RPWC] Downloading %s...' % self._pending_jobs_url)
    pollDeferred = self.getPage(self._pending_jobs_url)
    pollDeferred.addCallback(self._ProcessResults)
    pollDeferred.addErrback(log.err, '[RPWC] error')
    return pollDeferred

  def setServiceParent(self, parent):
    base.PollingChangeSource.setServiceParent(self, parent)
    self._try_job_rietveld = parent

  @defer.inlineCallbacks
  def _InitProcessedKeysCache(self):
    log.msg('[RPWC] Initializing processed keys cache...')

    # Get recent BuildBot buildsets. We limit the number of fetched buildsets
    # as otherwise fetching properties of all of them would take days.
    bsdicts = yield self.master.db.buildsets.getRecentBuildsets(
        MAX_RECENT_BUILDSETS_TO_INIT_CACHE)

    log.msg('[RPWC] Received %d buildset dicts' % len(bsdicts))

    def asNaiveUTC(dt):
      if dt is None:
        return datetime.datetime.now()
      if dt.tzinfo is None:
        return dt
      utc_datetime = dt.astimezone(pytz.utc)
      return utc_datetime.replace(tzinfo=None)

    # Compose a map of buildset ids to the submission timestamp.
    buildsets = {}
    for bsdict in bsdicts:
      bsid = bsdict.get('bsid')
      if bsid is not None:
        buildsets[bsid] = asNaiveUTC(bsdict.get('submitted_at'))

    log.msg('[RPWC] Processing %d buildsets' % len(buildsets))

    # Find jobs for each buildset and add them to the processed keys cache.
    self._processed_keys = {}
    for bsid in buildsets.keys():
      log.msg('[RPWC] Loading properties of the buildset %d' % bsid)
      bsprops = yield self.master.db.buildsets.getBuildsetProperties(bsid)
      if 'try_job_key' in bsprops:
        key = bsprops['try_job_key'][0]
        self._processed_keys[key] = buildsets[bsid]

    log.msg('[RPWC] Initialized processed keys cache from master with %d '
            'jobs.' % len(self._processed_keys))

  @defer.inlineCallbacks
  def _ProcessResults(self, first_page_json):
    """Processes all incoming jobs from Rietveld and submits new jobs."""
    results = json.loads(first_page_json)
    all_jobs = []

    # Initialize processed keys cache if needed. We can't do it in the
    # constructor as self.master, required for this, is not available then yet.
    if self._processed_keys is None:
      yield self._InitProcessedKeysCache()

    prev_cursor = None
    # TODO(sergiyb): Change logic to use 'more' field when it is implemented on
    # Rietveld. This field will indicate whether there are more pages.
    while len(results['jobs']) and prev_cursor != results['cursor']:
      all_jobs.extend(results['jobs'])
      next_url = self._pending_jobs_url + '&cursor=%s' % str(results['cursor'])
      prev_cursor = results['cursor']
      log.msg('[RPWC] Downloading %s...' % next_url)
      page_json = yield self.getPage(next_url)
      results = json.loads(page_json)

    log.msg('[RPWC] Retrieved %d jobs' % len(all_jobs))

    # Rietveld uses AppEngine NDB API, which serves naive UTC datetimes.
    cutoff_timestamp = datetime.datetime.utcnow() - datetime.timedelta(hours=6)

    log.msg('[RPWC] Cache contains %d jobs' % len(self._processed_keys))

    # Find new jobs and put them into cache.
    new_jobs = []
    for job in all_jobs:
      parsed_timestamp = str_to_datetime(job['timestamp'])
      # TODO(sergiyb): This logic relies on the assumption that we don't care
      # about jobs older than 6 hours. Once we stabilize Rietveld cursor, we
      # should get rid of this assumption. Also see, http://crbug.com/376537.
      if (parsed_timestamp > cutoff_timestamp and
          job['key'] not in self._processed_keys):
        new_jobs.append(job)

    if new_jobs:
      log.msg('[RPWC] Submitting %d new jobs...' % len(new_jobs))
      yield self._try_job_rietveld.SubmitJobs(new_jobs)
    else:
      log.msg('[RPWC] No new jobs.')

    # Update processed keys cache.
    new_processed_keys = {}
    for job in new_jobs:
      parsed_timestamp = str_to_datetime(job['timestamp'])
      new_processed_keys[job['key']] = parsed_timestamp
    log.msg('[RPWC] Added %d new jobs to the cache.' % len(new_processed_keys))

    num_removed = 0
    for processed_key, timestamp in self._processed_keys.iteritems():
      if timestamp > cutoff_timestamp:
        new_processed_keys[processed_key] = timestamp
      else:
        num_removed += 1
    log.msg('[RPWC] Removed %d old jobs from the cache.' % num_removed)
    self._processed_keys = new_processed_keys


class TryJobRietveld(TryJobBase):
  """A try job source that gets jobs from pending Rietveld patch sets."""

  def __init__(self, name, pools, properties=None, last_good_urls=None,
               code_review_sites=None, project=None, filter_master=False):
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

    self._poller = _RietveldPollerWithCache(endpoint, interval=10)
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

    url = 'get_pending_try_patchsets?limit=1000'

    # Filter by master name if specified.
    if filter_master:
      url += '&master=%s' % urllib.quote_plus(master_utils.GetMastername())

    return urlparse.urljoin(code_review_sites[project], url)

  def has_valid_user_list(self):
    """Returns true if the user poller is valid (has retrieved valid users)."""

    return self._valid_users.valid()

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
