#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_step testcases."""


import os
import shutil
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from common import chromium_utils
from master import chromium_step


class ChromiumStepTest(unittest.TestCase):

  def setUp(self):
    # Must use chromium_utils.AbsoluteCanonicalPath to avoid getting different
    # paths on Mac in the implementation of chromium_step.Prepend().
    self.output_dir = chromium_utils.AbsoluteCanonicalPath(
        tempfile.gettempdir())
    self.perf_output_dir = chromium_utils.AbsoluteCanonicalPath(
        os.path.join(tempfile.gettempdir(), 'perf'))

  def testPrependAllowed(self):
    temp_handle, temp_name = tempfile.mkstemp()
    chromium_step.Prepend(temp_name, '111', self.output_dir,
                          self.perf_output_dir)
    self.assertTrue(_readData(temp_name), '111')
    os.close(temp_handle)
    os.unlink(temp_name)

  def testPrependAllowedSubDir(self):
    # Use mkdtemp() just to generate a unique filename.
    temp_dir = tempfile.mkdtemp()
    temp_name = os.path.split(temp_dir)[1]
    os.rmdir(temp_dir)

    # Create a path containing a sub-directory of the output_dir. Make sure it
    # doesn't exist so we can verify it's created.
    subdir = os.path.join(self.output_dir, temp_name)
    if os.path.exists(subdir):
      shutil.rmtree(subdir)

    subdir_file = os.path.join(subdir, temp_name)
    chromium_step.Prepend(subdir_file, '222', self.output_dir,
                          self.perf_output_dir)

    # Verify the subdir was also created, in addition to the file.
    self.assertTrue(os.path.exists(subdir))
    self.assertTrue(os.path.exists(subdir_file))
    self.assertTrue(_readData(subdir_file), '222')

    os.remove(subdir_file)
    os.rmdir(subdir)

  def testPrependDenied(self):
    home_dir = os.path.expanduser("~")
    invalid_filename = tempfile.mkstemp(dir=home_dir)[1]

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
