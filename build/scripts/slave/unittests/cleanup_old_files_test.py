#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import tempfile
import time
import unittest

import test_env  # pylint: disable=W0403,W0611

import slave.cleanup_old_files as cleanup_old_files


class CleanupOldFilesTest(unittest.TestCase):
  def setUp(self):
    self.old_time = time.time
    self.old_getatime = os.path.getatime

    self.base_directory = tempfile.mkdtemp()
    self.sub_directory = tempfile.mkdtemp(dir=self.base_directory)
    tempfile.mkstemp(dir=self.sub_directory)

  def tearDown(self):
    time.time = self.old_time
    os.path.getatime = self.old_getatime

    shutil.rmtree(self.base_directory)

  def testBasicTest(self):
    # Ensure the file isn't found.
    os.path.getatime = lambda file : 0
    time.time = lambda : 0
    self.assertEqual(0,
                     len(cleanup_old_files.GetOldFiles(self.base_directory,
                                                       3600)))

    # Ensure the file is found.
    time.time = lambda : 10
    self.assertEqual(1,
                     len(cleanup_old_files.GetOldFiles(self.base_directory, 0)))


if __name__ == '__main__':
  unittest.main()
