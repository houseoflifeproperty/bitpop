#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import tempfile
import unittest

import test_env  # pylint: disable=W0403,W0611

import slave.zip_build as zip_build
from common import chromium_utils


class TestWriteRevisionFile(unittest.TestCase):
  def testWriteFile(self):
    tempdir = tempfile.mkdtemp()
    revision = '123'
    revision_filename = zip_build.WriteRevisionFile(tempdir, revision)

    self.assertEquals(revision, open(revision_filename).read().strip())
    self.assertTrue(os.path.exists(revision_filename))
    self.assertEquals(revision_filename,
                      os.path.join(tempdir,
                                   chromium_utils.FULL_BUILD_REVISION_FILENAME))


if __name__ == '__main__':
  unittest.main()
