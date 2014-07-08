#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Source file for master_utils testcases."""


import unittest

import test_env  # pylint: disable=W0611

from master import master_utils


class MasterUtilsTest(unittest.TestCase):

  def testPartition(self):
    partitions = master_utils.Partition([(1, 'a'),
                                         (2, 'b'),
                                         (3, 'c'),
                                         ], 2)
    self.assertEquals([['a', 'b'], ['c']], partitions)


if __name__ == '__main__':
  unittest.main()
