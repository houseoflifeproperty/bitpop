#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import os.path
import shutil
import simplejson
import tempfile
import unittest
import sys

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path.append(os.path.join(BASE_DIR, 'scripts'))
sys.path.append(os.path.join(BASE_DIR, 'site_config'))

from slave.chromium import archive_build
from common import archive_utils_unittest
from common import chromium_utils
import config


ZIP_TEST_FILES = ['file1.txt',
                  'file2.txt',
                  'file3.txt']

TEST_FILES = ['test1.exe',
              'test2.exe',
              os.path.join('dir1', 'test3.exe')]

TEST_FILES_NO_DEEP_DIRS = ['test1.exe',
                           'test2.exe']

EXTRA_TEST_FILES = ['extra_test1.exe',
                    'extra_test2.exe',
                    os.path.join('extra_dir1', 'extra_test3.exe')]


class MockOptions(object):
  """ Class used to mock the optparse options object for the Stager.
  """
  def __init__(self, src_dir, build_dir, target, archive_path,
               extra_archive_paths, build_number, default_chromium_revision,
               default_webkit_revision, default_v8_revision):
    self.src_dir = src_dir
    self.build_dir = build_dir
    self.target = target
    self.dirs = {
      'www_dir_base': archive_path,
      'symbol_dir_base': archive_path,
    }
    self.extra_archive_paths = extra_archive_paths
    self.build_number = build_number
    self.default_chromium_revision = default_chromium_revision
    self.default_webkit_revision = default_webkit_revision
    self.default_v8_revision = default_v8_revision
    self.installer = config.Archive.installer_exe
    self.factory_properties = {}


class PlatformError(Exception): pass
class InternalStateError(Exception): pass


class ArchiveTest(unittest.TestCase):
  # Attribute '' defined outside __init__
  # pylint: disable=W0201

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    archive_utils_unittest.BuildTestFilesTree(self.temp_dir)

    # Make some directories to make the stager happy.
    self.target = 'Test'
    if chromium_utils.IsWindows():
      self.build_dir = os.path.join(self.temp_dir, 'build')
    elif chromium_utils.IsLinux():
      self.build_dir = os.path.join(self.temp_dir, 'out')
    elif chromium_utils.IsMac():
      self.build_dir = os.path.join(self.temp_dir, 'xcodebuild')
    else:
      raise PlatformError(
          'Platform "%s" is not currently supported.' % sys.platform)
    os.makedirs(os.path.join(self.build_dir, self.target))
    self.src_dir = os.path.join(self.temp_dir, 'build', 'src')
    os.makedirs(self.src_dir)
    self.archive_dir = os.path.join(self.temp_dir, 'archive')
    os.makedirs(self.archive_dir)
    # Make a directory to hold an extra files and tests specifier:
    self.extra_files_dir = os.path.join(self.temp_dir, 'build', 'src', 'extra')
    os.makedirs(self.extra_files_dir)

    # Create the FILES file and seed with contents:
    self.extra_files = os.path.join(self.extra_files_dir, 'FILES')
    extra_file = open(self.extra_files, 'w')
    for f in ZIP_TEST_FILES:
      extra_file.write(f + '\n')
    extra_file.close()

    # Create the TESTS file and seed with contents:
    self.extra_tests = os.path.join(self.extra_files_dir, 'TESTS')
    extra_tests = open(self.extra_tests, 'w')
    for t in EXTRA_TEST_FILES:
      extra_tests.write(t + '\n')
    extra_tests.close()
    # The stager object will be initialized in initializeStager method.
    self.stager = None

  def initializeStager(self, build_number=None, default_chromium_revision=None,
                       default_webkit_revision=None, default_v8_revision=None):
    self.options = MockOptions(self.src_dir, self.build_dir, self.target,
                               self.archive_dir, self.extra_files_dir,
                               build_number, default_chromium_revision,
                               default_webkit_revision, default_v8_revision)
    if self.options.build_number:
      self.stager = archive_build.StagerByBuildNumber(self.options)
    else:
      self.stager = archive_build.StagerByChromiumRevision(self.options)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  def prepareToolDir(self):
    # Build up a directory for Zip file testing
    if chromium_utils.IsWindows():
      self.tool_dir = 'chrome/tools/build/win'
    elif chromium_utils.IsLinux():
      self.tool_dir = 'chrome/tools/build/linux'
    elif chromium_utils.IsMac():
      self.tool_dir = 'chrome/tools/build/mac'
    else:
      raise PlatformError(
          'Platform "%s" is not currently supported.' % sys.platform)
    self.tool_dir = os.path.join(self.src_dir, self.tool_dir)
    os.makedirs(self.tool_dir)

  def createTestFiles(self, file_list):
    self.prepareToolDir()

    self.TESTS = os.path.join(self.tool_dir, 'TESTS')
    f = open(self.TESTS, 'w')
    f.write('\n'.join(file_list))
    f.close()

    archive_utils_unittest.CreateFileSetInDir(
        os.path.join(self.build_dir, self.target), file_list)

  def createExtraTestFiles(self):
    if not self.tool_dir:
      raise InternalStateError('createTestFiles must be called first')

    for tf in EXTRA_TEST_FILES:
      dir_part = os.path.dirname(tf)
      if (dir_part):
        dir_path = os.path.join(self.build_dir, dir_part)
        os.makedirs(dir_path)

      test_file = open(os.path.join(self.build_dir, tf), 'w')
      test_file.write('contents')
      test_file.close()

  def testGetExtraFiles(self):
    expected_extra_files_list = ZIP_TEST_FILES[:]
    expected_extra_files_list.sort()

    self.initializeStager()
    extra_files_list = self.stager.GetExtraFiles('extra', 'FILES')
    extra_files_list.sort()

    self.assertEquals(expected_extra_files_list, extra_files_list)

  def testUploadTests(self):
    # This test is currently only applicable on Windows.
    if not chromium_utils.IsWindows():
      return

    self.createTestFiles(TEST_FILES)
    self.initializeStager()
    self.stager.UploadTests(self.archive_dir)

    expected_archived_tests = TEST_FILES
    archived_tests = os.listdir(os.path.join(self.archive_dir,
                                             'chrome-win32.test'))
    self.assertEquals(len(expected_archived_tests), len(archived_tests))

  def testUploadTestsWithExtras(self):
    # This test is currently only applicable on Windows.
    if not chromium_utils.IsWindows():
      return

    self.createTestFiles(TEST_FILES)
    self.createExtraTestFiles()
    self.initializeStager()
    self.stager.UploadTests(self.archive_dir)

    expected_archived_tests = TEST_FILES + EXTRA_TEST_FILES
    archived_tests = os.listdir(os.path.join(self.archive_dir,
                                             'chrome-win32.test'))
    self.assertEquals(len(expected_archived_tests), len(archived_tests))

  def testUploadTestsNoDeepPaths(self):
    # This test is currently only applicable on Windows.
    if not chromium_utils.IsWindows():
      return

    self.createTestFiles(TEST_FILES_NO_DEEP_DIRS)
    self.initializeStager()
    self.stager.UploadTests(self.archive_dir)

    expected_archived_tests = TEST_FILES_NO_DEEP_DIRS
    archived_tests = os.listdir(os.path.join(self.archive_dir,
                                             'chrome-win32.test'))
    self.assertEquals(len(expected_archived_tests), len(archived_tests))

  def testGenerateRevisionFile(self):
    build_number = None
    chromium_revision = 12345
    webkit_revision = 54321
    v8_revision = 33333
    self.initializeStager(build_number, chromium_revision, webkit_revision,
                          v8_revision)
    self.stager.GenerateRevisionFile()
    self.assertTrue(os.path.exists(self.stager.revisions_path))
    self.assertEquals(None, self.stager.GetLastBuildRevision())
    fp = open(self.stager.revisions_path)
    revisions_dict = simplejson.loads(fp.read())
    self.assertEquals(self.stager.last_chromium_revision,
                      revisions_dict['chromium_revision'])
    self.assertEquals(self.stager.last_webkit_revision,
                      revisions_dict['webkit_revision'])
    self.assertEquals(self.stager.last_v8_revision,
                      revisions_dict['v8_revision'])
    fp.close()

  def testSaveToLastChangeFileAndGetLastBuildRevisionByChromiumRevision(self):
    """This test is to test function SaveBuildRevisionToSpecifiedFile and
    GetLastBuildRevision when acrchiving by chromium revision.
    """
    build_number = None
    chromium_revision = 12345
    webkit_revision = 54321
    v8_revision = 33333
    expect_last_change_file_contents = '%d' % (chromium_revision)
    self.initializeStager(build_number, chromium_revision, webkit_revision,
                          v8_revision)
    last_change_file_path = self.stager.last_change_file
    # At first, there is no last change file.
    self.assertFalse(os.path.exists(last_change_file_path))
    self.assertEquals(None, self.stager.GetLastBuildRevision())
    # Save the revision information to last change file.
    self.stager.SaveBuildRevisionToSpecifiedFile(last_change_file_path)
    # Check the contents in last change file.
    self.assertTrue(os.path.exists(last_change_file_path))
    fp = open(last_change_file_path)
    self.assertEquals(expect_last_change_file_contents, fp.read())
    fp.close()
    self.assertEquals(chromium_revision, self.stager.GetLastBuildRevision())

  def testSaveToLastChangeFileAndGetLastBuildRevisionByBuildNumber(self):
    """This test is to test function SaveBuildRevisionToSpecifiedFile and
    GetLastBuildRevision when acrchiving by build number.
    """
    build_number = 99999
    chromium_revision = 12345
    webkit_revision = 54321
    v8_revision = 33333
    expect_last_change_file_contents = '%d' % (build_number)
    self.initializeStager(build_number, chromium_revision, webkit_revision,
                          v8_revision)
    last_change_file_path = self.stager.last_change_file
    # At first, there is no last change file.
    self.assertFalse(os.path.exists(last_change_file_path))
    self.assertEquals(None, self.stager.GetLastBuildRevision())
    # Save the revision information to last change file.
    self.stager.SaveBuildRevisionToSpecifiedFile(last_change_file_path)
    # Check the contents in last change file.
    self.assertTrue(os.path.exists(last_change_file_path))
    fp = open(last_change_file_path)
    self.assertEquals(expect_last_change_file_contents, fp.read())
    fp.close()
    self.assertEquals(build_number, self.stager.GetLastBuildRevision())


if __name__ == '__main__':
  # Run with a bit more output.
  suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveTest)
  unittest.TextTestRunner(verbosity=2).run(suite)
