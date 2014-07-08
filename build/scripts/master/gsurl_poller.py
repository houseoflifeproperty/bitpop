# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This PollingChangeSource polls a Google Storage URL for change revisions.

Each change is submitted to change master which triggers build steps.

Notice that the gsutil configuration (.boto file) must be setup in either the
default location (home dir) or by using the environment variables
AWS_CREDENTIAL_FILE and BOTO_CONFIG.

Example:
To poll a change in Chromium build snapshots, use -
from master import gsurl_poller
changeurl = 'gs://chromium-browser-snapshots/Linux/LAST_CHANGE'
poller = gsurl_poller.GSURLPoller(changeurl=changeurl, pollInterval=10800)
c['change_source'] = [poller]
"""

import os
import sys

from twisted.internet import defer
from twisted.python import log

from buildbot.changes import base

from common import chromium_utils


BASE_DIR = os.path.abspath(os.path.join(
               os.path.dirname(__file__), os.pardir, os.pardir))
GSUTIL_DIR = os.path.join(BASE_DIR, 'third_party', 'gsutil')
BOTO_FILE = os.path.join(BASE_DIR, 'site_config', '.boto')


class GSURLPoller(base.PollingChangeSource):
  """Poll a Google Storage URL for change number and submit to change master."""

  compare_attrs = ['changeurl', 'pollInterval']

  # pylint runs this against the wrong buildbot version.
  # In buildbot 8.4 base.PollingChangeSource has no __init__
  # pylint: disable=W0231
  def __init__(self, changeurl, pollInterval=5*60, category=None):
    """Initialize GSURLPoller.

    Args:
    changeurl: URL to a file containing the last change revision.
    pollInterval: Time (in seconds) between queries for changes.
    category: Build category to trigger (optional).
    """
    if not changeurl.startswith('gs://'):
      raise Exception('GSURLPoller changeurl must start with gs://')

    self.changeurl = changeurl
    self.pollInterval = pollInterval
    self.category = category
    self.last_change = None
    self.gsutil = os.path.join(GSUTIL_DIR, 'gsutil')

    # Make sure gsutil uses the right boto file for authentication.
    self.env = os.environ.copy()
    self.env['AWS_CREDENTIAL_FILE'] = BOTO_FILE
    self.env['BOTO_CONFIG'] = BOTO_FILE

  def describe(self):
    return 'GSURLPoller watching %s' % self.changeurl

  def poll(self):
    log.msg('GSURLPoller polling %s' % self.changeurl)
    d = defer.succeed(None)
    d.addCallback(self._process_changes)
    d.addErrback(self._finished_failure)
    return d

  def _finished_failure(self, res):
    log.msg('GSURLPoller poll failed: %s. URL: %s' % (res, self.changeurl))

  def _process_changes(self, _change):
    capture = chromium_utils.FilterCapture()
    cmd = [sys.executable, self.gsutil, 'cat', self.changeurl]
    ret = chromium_utils.RunCommand(cmd, filter_obj=capture, env=self.env)
    parsed_revision = capture.text[0].strip()

    if ret != 0:
      raise RuntimeError(
          'GSURLPoller poll failed with exit code: %s.\nCmd: %s.\nURL: %s\n'
          'Error messages: %s. ' %
          (ret, ' '.join(cmd), self.changeurl, '\n'.join(capture.text)))
    log.msg('GSURLPoller finished polling %s' % self.changeurl)
    if self.last_change != parsed_revision:
      self.master.addChange(who='gsurl_poller',
                            files=[],
                            revision=parsed_revision,
                            comments='comment',
                            category=self.category)
      self.last_change = parsed_revision
