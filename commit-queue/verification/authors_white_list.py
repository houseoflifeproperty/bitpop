# coding=utf8
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Ignores issues not passing a authors regex."""

import re

from verification import base


class AuthorVerifier(base.Verifier):
  """Needs the author to match at least one regexp in self.regex."""
  name = 'author_white_list'

  def __init__(self, author_white_list):
    super(AuthorVerifier, self).__init__()
    self.author_white_list = author_white_list

  def verify(self, pending):
    if not any(re.match(r, pending.owner) for r in self.author_white_list):
      pending.verifications[self.name] = base.SimpleStatus(
          state=base.FAILED,
          error_message='Can\'t commit because the owner %s not in whitelist' %
              pending.owner)
    else:
      pending.verifications[self.name] = base.SimpleStatus(base.SUCCEEDED)

  def update_status(self, queue):
    pass
