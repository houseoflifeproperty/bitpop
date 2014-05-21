#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import time
import unittest

import test_env  # pylint: disable=W0611

from master.failures_history import FailuresHistory


class FailuresHistoryTest(unittest.TestCase):
  def setUp(self):
    super(FailuresHistoryTest, self).setUp()
    # Store time.time as some test cases may replace it.
    self._old_time_time = time.time

  def tearDown(self):
    time.time = self._old_time_time
    super(FailuresHistoryTest, self).tearDown()

  def test_trivial(self):
    # Put some failures and make sure they're there.
    # No failures are expected to expire or dropped due to size limit.
    h = FailuresHistory(expiration_time=3600, size_limit=1024)
    self.assertEqual(h.GetCount(42), 0)
    h.Put(42)
    self.assertEqual(h.GetCount(42), 1)
    h.Put(42)
    self.assertEqual(h.GetCount(42), 2)
    h.Put(13)
    self.assertEqual(h.GetCount(13), 1)
    self.assertEqual(h.GetCount(42), 2)
    self.assertEqual(h.GetCount(77), 0)

  def test_timer(self):
    # Test that the expiration_time works as expected.
    # The size of the history is large enough to avoid dropping.
    current_time = 0
    time.time = lambda: current_time

    h = FailuresHistory(expiration_time=5, size_limit=1024)
    for _ in xrange(100):
      h.Put(42)
      current_time += 1
    self.assertEqual(h.GetCount(42), 4)
    for _ in xrange(16):
      h.Put(42)
    self.assertEqual(h.GetCount(42), 20)
    current_time += 10
    self.assertEqual(h.GetCount(42), 0)

  def test_maxsize(self):
    # Test that size_limit works as expected.
    # No failures should expire.
    h = FailuresHistory(expiration_time=3600, size_limit=4)
    self.assertEqual(h.GetCount(42), 0)
    h.Put(42)
    self.assertEqual(h.GetCount(42), 1)
    h.Put(42)
    self.assertEqual(h.GetCount(42), 2)
    h.Put(42)
    self.assertEqual(h.GetCount(42), 3)
    h.Put(42)
    self.assertEqual(h.GetCount(42), 4)
    h.Put(13)  # 4+1 = 5 > size_limit  ->  drop one old '42' failure.
    self.assertEqual(h.GetCount(13), 1)
    self.assertEqual(h.GetCount(42), 3)

  def test_stress_maxsize(self):
    TEST_SIZE = 137
    h = FailuresHistory(expiration_time=3600, size_limit=TEST_SIZE)
    # Many different failures
    for f in xrange(10000):
      h.Put(f)
      # Make sure we always know about the newly added failure.
      self.assertTrue(h.GetCount(f) == 1)

    # Many failures with the same ID -> should drop most of the other failures.
    for _ in xrange(TEST_SIZE * 2):
      h.Put(42)
    self.assertTrue(h.GetCount(42) > 0)

    for _ in xrange(10000):
      h.Put(42)
      # Make sure there's always enough of repeating failures.
      self.assertTrue(h.GetCount(42) >= TEST_SIZE/2)


if __name__ == '__main__':
  unittest.main()
