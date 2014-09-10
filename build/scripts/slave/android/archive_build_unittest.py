#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import os.path
import shutil
import tempfile
import unittest
import sys
import zipfile

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path.append(os.path.join(BASE_DIR, 'scripts'))
sys.path.append(os.path.join(BASE_DIR, 'site_config'))

from slave.android import archive_build
from common import archive_utils_unittest


BINARY_FILES = ['test1.apk',
                'test2.apk',
                'lib1.so',
                'lib2.so',
                 os.path.join('dir1', 'test3.apk'),
                 os.path.join('dir2', 'lib3.so')]

INTERMEDIATE_FILES = ['test1.o',
                      'test2.o',
                      'lib1.o',
                      'lib2.o',
                      os.path.join('dir1', 'test3.o'),
                      os.path.join('dir2', 'lib3.o')]

SOURCE_FILES = ['a.cpp']

class ArchiveTest(unittest.TestCase):

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    archive_utils_unittest.BuildTestFilesTree(self.temp_dir)
    self.zip_file = 'archive.zip'
    self.target = 'Debug'
    self.build_dir = os.path.join(self.temp_dir, 'build')
    os.makedirs(self.build_dir)
    self.src_dir = os.path.join(self.build_dir, 'src')
    os.makedirs(self.src_dir)
    self.out_dir = os.path.join(self.src_dir, 'out')
    os.makedirs(self.out_dir)
    self.target_dir = os.path.join(self.out_dir, self.target)
    os.makedirs(self.target_dir)

    # Create test files
    archive_utils_unittest.CreateFileSetInDir(self.src_dir, SOURCE_FILES)
    archive_utils_unittest.CreateFileSetInDir(self.target_dir, BINARY_FILES)
    archive_utils_unittest.CreateFileSetInDir(self.target_dir,
        INTERMEDIATE_FILES)
    os.chdir(self.src_dir)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  def verifyZipFile(self, zip_dir, zip_file_path, expected_files):
    # Extract the files from the archive
    extract_dir = os.path.join(zip_dir, 'extract')
    os.makedirs(extract_dir)
    zip_file = zipfile.ZipFile(zip_file_path)
    if hasattr(zip_file, 'extractall'):
      zip_file.extractall(extract_dir)  # pylint: disable=E1101
      def FindFiles(arg, dirname, names):
        subdir = dirname[len(arg):].strip(os.path.sep)
        extracted_files.extend([os.path.join(subdir, name) for name in names if
                                os.path.isfile(os.path.join(dirname, name))])
      extracted_files = []
      os.path.walk(extract_dir, FindFiles, extract_dir)
      self.assertEquals(len(expected_files), len(extracted_files))
      for f in extracted_files:
        self.assertIn(f, expected_files)
    else:
      test_result = zip_file.testzip()
      self.assertTrue(not test_result)
    zip_file.close()

  def testArchiveBuild(self):
    archive_build.archive_build(self.target, name=self.zip_file, location='out')
    zip_file_path = os.path.join(self.out_dir, self.zip_file)

    self.assertTrue(os.path.exists(zip_file_path))
    files_list = [os.path.join('out', self.target, x) for x in (BINARY_FILES +
        INTERMEDIATE_FILES)]
    self.verifyZipFile(self.out_dir, zip_file_path, files_list)

  def testArchiveBuildIgnoreSubfolderNames(self):
    archive_build.archive_build(self.target, name=self.zip_file, location='out',
        ignore_subfolder_names=True)
    zip_file_path = os.path.join(self.out_dir, self.zip_file)

    self.assertTrue(os.path.exists(zip_file_path))
    files_list = [os.path.basename(x) for x in (BINARY_FILES +
        INTERMEDIATE_FILES)]
    self.verifyZipFile(self.out_dir, zip_file_path, files_list)

  def testArchiveBuildWithFiles(self):
    files = ['*dir1/test3.o', '../../a.cpp']
    archive_build.archive_build(self.target, name=self.zip_file, location='out',
        files=files)
    zip_file_path = os.path.join(self.out_dir, self.zip_file)

    self.assertTrue(os.path.exists(zip_file_path))
    files_list = [os.path.join('out', self.target, 'dir1', 'test3.o'), 'a.cpp']
    self.verifyZipFile(self.out_dir, zip_file_path, files_list)

  def testArchiveBuildWithFilters(self):
    filters = ['*.so']
    archive_build.archive_build(self.target, name=self.zip_file, location='out',
        filters=filters)
    zip_file_path = os.path.join(self.out_dir, self.zip_file)

    self.assertTrue(os.path.exists(zip_file_path))
    files_list = [os.path.join('out', self.target, 'dir2', 'lib3.so'),
      os.path.join('out', self.target, 'lib1.so'),
      os.path.join('out', self.target, 'lib2.so')]
    self.verifyZipFile(self.out_dir, zip_file_path, files_list)

if __name__ == '__main__':
  suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveTest)
  unittest.TextTestRunner(verbosity=2).run(suite)
