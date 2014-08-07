#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import difflib
import glob
import os
import subprocess
import sys
import unittest

import test_env  # pylint: disable=W0403,W0611

import slave.patch_path_filter as patch_path_filter

from depot_tools_patch.test_support.patches_data import GIT, RAW

class ParsePatchSetTest(unittest.TestCase):
  """Test the patch_path_filter.parse_patch_set function with a variety of data.

  Notice that only patch data from patches_data.py that contains the Index: line
  is used, since that's only what's supported.
  The chunks in the patch data is sorted according to the details in the
  PatchSet class of patch.py, which orders different chunks differently
  depending on the kind of change it is.
  """
  def test_git_empty(self):
    patchset = patch_path_filter.parse_git_patch_set('')
    self.assertEqual(0, len(patchset.filenames))

  def test_svn_empty(self):
    patchset = patch_path_filter.parse_svn_patch_set('')
    self.assertEqual(0, len(patchset.filenames))

  def test_git_patch(self):
    patch_data = 'Index: chrome/file.cc\n' + GIT.PATCH
    patchset = patch_path_filter.parse_git_patch_set(patch_data)
    self._verify_patch(patchset)

  def test_svn_patch(self):
    patchset = patch_path_filter.parse_svn_patch_set(RAW.PATCH)
    self._verify_patch(patchset)

  def test_git_patch_two_files(self):
    patch_data = 'Index: chrome/file.cc\n' + GIT.PATCH + GIT.RENAME
    patchset = patch_path_filter.parse_git_patch_set(patch_data)
    self.assertEqual(2, len(patchset.filenames))
    self.assertEqual('tools/run_local_server.sh', patchset.filenames[0])
    self.assertEqual('chrome/file.cc', patchset.filenames[1])

  def test_svn_patch_two_files(self):
    patchset = patch_path_filter.parse_svn_patch_set(RAW.PATCH + RAW.DIFFERENT)
    self.assertEqual(2, len(patchset.filenames))
    self.assertEqual('chrome/file.cc', patchset.filenames[0])
    self.assertEqual('master/unittests/data/processes-summary.dat',
                     patchset.filenames[1])

  def test_patches_on_disk(self):
    script = os.path.join(test_env.RUNTESTS_DIR, os.pardir,
                          'patch_path_filter.py')
    data_dir = os.path.join(test_env.DATA_PATH, 'patch_path_filter')
    # The args files decides how many variations of tests we'll run per patch.
    for args_file in glob.glob(os.path.join(data_dir, '*.args*')):
      arg_parts = args_file.split('.args')
      test_case = arg_parts[0]
      index = arg_parts[1]
      patch_file = test_case + '.patch'
      self.assertTrue(os.path.exists(patch_file))

      output_file = test_case + '.output' + index
      self.assertTrue(os.path.exists(output_file))

      input_data = open(patch_file).read()
      args = open(args_file).read().strip().split(' ')
      expected_output = open(output_file).read()
      env = os.environ.copy()
      env['PYTHONPATH'] = os.pathsep.join(sys.path)
      script_process = subprocess.Popen([sys.executable, script] + args,
                                        env=env,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
      output = script_process.communicate(input=input_data)[0]
      self.assertEquals(expected_output, output,
          'Output from filtering patch file:\n%s\n'
          'using arguments "%s" is not '
          'equal to expected output in:\n%s\n'
          'Diff (notice the indentation!):\n%s\n' %
          (patch_file, args, output_file,
           _display_diff(expected_output, output)))

  def _verify_patch(self, patchset):
    self.assertEqual(1, len(patchset.filenames))
    self.assertEqual('chrome/file.cc', patchset.filenames[0])
    self.assertEqual('hh\n', patchset[0].dump()[-3:])


def _display_diff(expected, actual):
  diff = difflib.unified_diff(expected.splitlines(),
                              actual.splitlines())
  return '\n'.join(list(diff))


class ConvertToPatchCompatibleDiffTest(unittest.TestCase):
  def test_git(self):
    diff = patch_path_filter.convert_to_patch_compatible_diff('chrome/file.cc',
                                                              GIT.PATCH)
    self._verify_diff(diff)

  def test_git_from_rietveld(self):
    data = 'Index: chrome/file.cc\n' + GIT.PATCH
    diff = patch_path_filter.convert_to_patch_compatible_diff('chrome/file.cc',
                                                              data)
    self._verify_diff(diff)

  def test_svn(self):
    diff = patch_path_filter.convert_to_patch_compatible_diff('chrome/file.cc',
                                                              RAW.PATCH)
    self._verify_diff(diff)

  def _verify_diff(self, diff):
    lines = diff.splitlines()
    self.assertEquals('Index: chrome/file.cc', lines[0])
    self.assertTrue('--- chrome/file.cc' in diff)
    self.assertTrue('+++ chrome/file.cc' in diff)

if __name__ == '__main__':
  unittest.main()
