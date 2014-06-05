# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This PollingChangeSource polls a URL for the change number.

Each change is submited to change master which triggers build steps.

Example:
To poll a change in Chromium build snapshots, use -
from buildbot.changes import url_poller
changeurl = 'http://commondatastorage.googleapis.com/'
            'chromium-browser-snapshots/Linux/LAST_CHANGE'
poller = urlpoller.URLPoller(changeurl=changeurl, pollInterval=10800)
c['change_source'] = [poller]
"""

from twisted.python import log
from twisted.web.client import getPage

from buildbot.changes import base


class URLPoller(base.PollingChangeSource):
  """Poll a URL for change number and submit to change master."""

  compare_attrs = ['changeurl', 'pollInterval']

  # pylint runs this against the wrong buildbot version.
  # In buildbot 8.4 base.PollingChangeSource has no __init__
  # pylint: disable=W0231
  def __init__(self, changeurl, pollInterval=3600, category=None,
               include_revision=False):
    """Initialize URLPoller.

    Args:
    changeurl: The URL to change number.
    pollInterval: The time (in seconds) between queries for
                          changes (default is 1 hour)
    include_revision: If True, interpret the body of the changeurl as a
                      revision.
    """
    self.changeurl = changeurl
    self.pollInterval = pollInterval
    self.category = category
    self.include_revision = include_revision
    self.last_change = None

  def describe(self):
    return 'URLPoller watching %s' % self.changeurl

  def poll(self):
    log.msg('URLPoller polling %s' % self.changeurl)
    d = getPage(self.changeurl, timeout=self.pollInterval)
    d.addCallback(self._process_changes)
    d.addErrback(self._finished_failure)
    return d

  def _finished_failure(self, res):
    log.msg('URLPoller poll failed: %s. URL: %s' % (res, self.changeurl))

  def _process_changes(self, change):
    log.msg('URLPoller finished polling %s' % self.changeurl)
    # Skip calling addChange() if this is the first successful poll.
    if self.last_change != change:
      extra = {}
      if self.include_revision:
        extra['revision'] = change.strip()
      self.master.addChange(author='urlpoller',
                            files=[],
                            comments='Polled from %s' % self.changeurl,
                            category=self.category,
                            **extra)
    self.last_change = change
