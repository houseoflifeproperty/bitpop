#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_step testcases."""


import os
import shutil
import string
import random
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from common import chromium_utils
from master import chromium_step


class ChromiumStepTest(unittest.TestCase):

  def setUp(self):
    # Must use chromium_utils.AbsoluteCanonicalPath to avoid getting different
    # paths on Mac in the implementation of chromium_step.Prepend().
    self.output_dir = chromium_utils.AbsoluteCanonicalPath(tempfile.mkdtemp())
    self.perf_output_dir = chromium_utils.AbsoluteCanonicalPath(
        os.path.join(self.output_dir, 'perf'))

  def tearDown(self):
    shutil.rmtree(self.output_dir)

  @staticmethod
  def _generateTempName(base_dir):
    while True:
      candidate = ''.join(random.choice(string.ascii_letters + string.digits)
                          for _ in xrange(8))
      path = os.path.join(base_dir, candidate)
      if not os.path.exists(path):
        return candidate

  def testPrependAllowed(self):
    with tempfile.NamedTemporaryFile(dir=self.output_dir) as temp_file:
      chromium_step.Prepend(temp_file.name, '111', self.output_dir,
                            self.perf_output_dir)
      self.assertTrue(_readData(temp_file.name), '111')

  def testPrependAllowedSubDir(self):
    # Use mkdtemp() just to generate a unique filename.
    temp_name = self._generateTempName(self.output_dir)

    # Create a path containing a sub-directory of the output_dir. Make sure it
    # doesn't exist so we can verify it's created.
    subdir = os.path.join(self.output_dir, temp_name)

    subdir_file = os.path.join(subdir, temp_name)
    self.assertFalse(os.path.exists(subdir_file))
    try:
      chromium_step.Prepend(subdir_file, '222', self.output_dir,
                            self.perf_output_dir)

      # Verify the subdir was also created, in addition to the file.
      self.assertTrue(os.path.exists(subdir))
      self.assertTrue(os.path.exists(subdir_file))
      self.assertTrue(_readData(subdir_file), '222')
    finally:
      shutil.rmtree(subdir)

  def testPrependDenied(self):
    with tempfile.NamedTemporaryFile() as fd:
      invalid_filename = fd.name
      def dummy_func():
        chromium_step.Prepend(invalid_filename, '333', self.output_dir,
                              self.perf_output_dir)
      self.assertRaises(Exception, dummy_func)

def _readData(filename):
  f = open(filename, 'r')
  data = f.read()
  f.close()
  return data


if __name__ == '__main__':
  unittest.main()
