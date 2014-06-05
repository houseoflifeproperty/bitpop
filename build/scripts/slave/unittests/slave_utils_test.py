#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import test_env  # pylint: disable=W0403,W0611

import mock
import slave.slave_utils as slave_utils
from common import chromium_utils

# build/scripts/slave/unittests
_SCRIPT_DIR = os.path.dirname(__file__)
_BUILD_DIR = os.path.abspath(os.path.join(
    _SCRIPT_DIR, os.pardir, os.pardir))

class TestGetZipFileNames(unittest.TestCase):
  def setUp(self):
    super(TestGetZipFileNames, self).setUp()
    chromium_utils.OverridePlatformName(sys.platform)

  def testNormalBuildName(self):
    (base_name, version_suffix) = slave_utils.GetZipFileNames({}, 123)
    self._verifyBaseName(base_name)
    self.assertEqual('_123', version_suffix)

  def testNormalBuildNameTryBot(self):
    build_properties = {'mastername': 'master.tryserver.chromium',
                        'buildnumber': 666}
    (base_name, version_suffix) = slave_utils.GetZipFileNames(
        build_properties, 123)
    self._verifyBaseName(base_name)
    self.assertEqual('_666', version_suffix)

  def testNormalBuildNameTryBotExtractNoParentBuildNumber(self):
    build_properties = {'mastername': 'master.tryserver.chromium',
                        'buildnumber': 666}
    def dummy():
      slave_utils.GetZipFileNames(build_properties, 123, extract=True)
    self.assertRaises(Exception, dummy)

  def testNormalBuildNameTryBotExtractWithParentBuildNumber(self):
    build_properties = {'mastername': 'master.tryserver.chromium',
                        'buildnumber': 666,
                        'parent_buildnumber': 999}
    (base_name, version_suffix) = slave_utils.GetZipFileNames(
        build_properties, 123, extract=True)
    self._verifyBaseName(base_name)
    self.assertEqual('_999', version_suffix)

  def testWebKitName(self):
    (base_name, version_suffix) = slave_utils.GetZipFileNames({}, 123, 456)
    self._verifyBaseName(base_name)
    self.assertEqual('_wk456_123', version_suffix)

  def _verifyBaseName(self, base_name):
    self.assertEqual('full-build-%s' % sys.platform, base_name)


class TestGetBuildRevisions(unittest.TestCase):
  def testNormal(self):
    (build_revision, webkit_revision) = slave_utils.GetBuildRevisions(
        _BUILD_DIR)
    self.assertTrue(build_revision > 0)
    self.assertEquals(None, webkit_revision)

  def testWebKitDir(self):
    (build_revision, webkit_revision) = slave_utils.GetBuildRevisions(
        _BUILD_DIR, webkit_dir=_BUILD_DIR)
    self.assertTrue(build_revision > 0)
    self.assertTrue(webkit_revision > 0)

  def testRevisionDir(self):
    (build_revision, webkit_revision) = slave_utils.GetBuildRevisions(
        _BUILD_DIR, revision_dir=_BUILD_DIR)
    self.assertTrue(build_revision > 0)
    self.assertEquals(None, webkit_revision)


class TestGSUtil(unittest.TestCase):
  @mock.patch('__main__.slave_utils.GSUtilSetup', return_value='/mock/gsutil')
  @mock.patch('__main__.chromium_utils.RunCommand')
  def testGSUtilCopyCacheControl(self, # pylint: disable=R0201
                                 run_command_mock, gs_util_setup_mock):
    slave_utils.GSUtilCopyFile('foo', 'bar',
      cache_control='mock_cache')
    run_command_mock.assert_called_with(['/mock/gsutil', '-h',
      'Cache-Control:mock_cache', 'cp', 'file://foo',
      'file://bar/foo'])
    slave_utils.GSUtilCopyDir('foo', 'bar',
      cache_control='mock_cache')
    run_command_mock.assert_called_with(['/mock/gsutil', '-m', '-h',
      'Cache-Control:mock_cache', 'cp', '-R', 'foo', 'bar'])


if __name__ == '__main__':
  unittest.main()
