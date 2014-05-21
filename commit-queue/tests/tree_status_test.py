#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/tree_status.py."""

import calendar
import json
import logging
import os
import StringIO
import sys
import unittest
import urllib2

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

# From tests/
import mocks

from verification import tree_status


class TreeStatusTest(mocks.TestCase):
  def setUp(self):
    super(TreeStatusTest, self).setUp()
    reference = calendar.timegm((2010, 1, 1, 12, 0, 0, 0, 0, -1))
    self.mock(tree_status.time, 'time', lambda: reference)
    self.urlrequests = []
    self.mock(urllib2, 'urlopen', self._urlopen)

  def tearDown(self):
    self.assertEqual([], self.urlrequests)
    super(TreeStatusTest, self).setUp()

  def _urlopen(self, _):
    return StringIO.StringIO(json.dumps(self.urlrequests.pop(0)))

  def test_fail(self):
    self.urlrequests = [
      [
        {
          'date': '2010-01-01 11:56:00.0',
          'general_state': 'open',
          'message': 'Foo',
        },
        {
          'date': '2010-01-01 11:57:00.0',
          'general_state': 'closed',
          'message': 'Bar',
        },
        {
          'date': '2010-01-01 11:58:00.0',
          'general_state': 'open',
          'message': 'Baz',
        },
      ],
    ]
    obj = tree_status.TreeStatus(tree_status_url='foo')
    self.assertEqual(True, obj.postpone())
    self.assertEqual(u'Tree is currently closed: Bar', obj.why_not())

  def test_pass(self):
    self.urlrequests = [
      [
        {
          'date': '2010-01-01 11:54:00.0',
          'general_state': 'open',
          'message': 'Foo',
        },
        {
          'date': '2010-01-01 11:57:00.0',
          'general_state': 'open',
          'message': 'Bar',
        },
        {
          'date': '2010-01-01 11:53:00.0',
          'general_state': 'closed',
          'message': 'Baz',
        },
      ],
    ]
    obj = tree_status.TreeStatus(tree_status_url='foo')
    self.assertEqual(False, obj.postpone())
    self.assertEqual(None, obj.why_not())

  def test_state(self):
    t = tree_status.TreeStatus(tree_status_url='foo')
    self.assertEqual(tree_status.base.SUCCEEDED, t.get_state())


if __name__ == '__main__':
  logging.basicConfig(
      level=[logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][
        min(sys.argv.count('-v'), 3)],
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
