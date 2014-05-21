# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Postpone commits until the tree is open."""

import calendar
import json
import logging
import time
import urllib2

from verification import base


class TreeStatus(base.IVerifierStatus):
  tree_status_url = unicode
  issue = int
  last_tree_status = unicode

  def get_state(self):
    return base.SUCCEEDED

  def postpone(self):
    self.last_tree_status = u''
    try:
      logging.debug('Fetching tree status for %s' % self.tree_status_url)
      now = time.time()
      cutoff = now - 5 * 60
      url = self.tree_status_url + '/allstatus?format=json&endTime=%d' % cutoff
      data = json.load(urllib2.urlopen(url))

      # Convert datetime string to epoch.
      for item in data:
        # The time is returned in UTC.
        x = time.strptime(item['date'].split('.', 1)[0], '%Y-%m-%d %H:%M:%S')
        item['date'] = calendar.timegm(x)

      for item in sorted(data, key=lambda x: x['date'], reverse=True):
        if item['general_state'] != 'open':
          logging.warn('Tree was closed %ds ago: %d',
              int(now - item['date']), self.issue)
          self.last_tree_status = unicode(item['message'])
          return True
        if item['date'] < cutoff:
          break
      return False
    except (urllib2.URLError, ValueError):
      logging.error('Failed to request tree status! %s' % url)
      return True

  def why_not(self):
    if self.last_tree_status:
      return u'Tree is currently closed: %s' % self.last_tree_status


class TreeStatusVerifier(base.Verifier):
  """Checks the tree status before allowing a commit."""
  name = 'tree status'

  def __init__(self, tree_status_url):
    super(TreeStatusVerifier, self).__init__()
    self.tree_status_url = tree_status_url

  def verify(self, pending):
    pending.verifications[self.name] = TreeStatus(
        tree_status_url=self.tree_status_url, issue=pending.issue)

  def update_status(self, queue):
    pass
