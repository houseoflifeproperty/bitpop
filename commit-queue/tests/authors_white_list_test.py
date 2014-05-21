#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/authors_white_list.py."""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

from verification import base
from verification import authors_white_list

# From tests/
import mocks


class AuthorTest(mocks.TestCase):
  def test_rejected(self):
    self.pending.owner = 'georges@micro.com'
    self._check(
        'Can\'t commit because the owner %s not in whitelist' %
        self.pending.owner)

  def test_allowed(self):
    self.pending.owner = 'georges@example.com'
    self._check(None)

  def _check(self, error_message):
    ver = authors_white_list.AuthorVerifier([r'^[\-\w]+\@example\.com$'])
    ver.verify(self.pending)
    ver.update_status([self.pending])
    name = authors_white_list.AuthorVerifier.name
    self.assertEquals(self.pending.verifications.keys(), [name])
    self.assertEquals(
        self.pending.verifications[name].error_message, error_message)
    if error_message:
      self.assertEquals(
          self.pending.verifications[name].get_state(), base.FAILED)
    else:
      self.assertEquals(
          self.pending.verifications[name].get_state(), base.SUCCEEDED)


if __name__ == '__main__':
  unittest.main()
