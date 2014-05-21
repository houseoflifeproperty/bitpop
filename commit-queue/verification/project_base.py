# coding=utf8
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Ignores issues not using the right project base url regex."""

import logging
import os
import re

import find_depot_tools  # pylint: disable=W0611
import breakpad

from verification import base


class ProjectBaseUrlVerifier(base.Verifier):
  """Needs the project base url to match at least one regexp in self.regex."""
  name = 'project_bases'

  def __init__(self, project_bases):
    super(ProjectBaseUrlVerifier, self).__init__()
    self.project_bases = project_bases

  def verify(self, pending):
    matches = filter(
        None, (re.match(r, pending.base_url) for r in self.project_bases))
    if not matches:
      logging.info('%s not in whitelist' % pending.base_url)
      state = base.IGNORED
    else:
      if len(matches) != 1:
        breakpad.SendStack(
            Exception('pending.base_url triggered multiple matches'), '')
      match = matches[0]
      if match.lastindex:
        pending.relpath = match.group(match.lastindex).lstrip('/').replace(
            '/', os.sep)
      state = base.SUCCEEDED
    pending.verifications[self.name] = base.SimpleStatus(state)

  def update_status(self, queue):
    pass
