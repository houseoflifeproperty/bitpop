#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for runbuild.py.

This is a basic check that runbuild.py can load masters properly.

"""

import os
import sys
import unittest

import test_env  # pylint: disable=W0403,W0611

from common import chromium_utils


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def runScript(*args, **kwargs):
  env = os.environ.copy()
  env['PYTHONPATH'] = os.pathsep.join(sys.path)
  return chromium_utils.RunCommand(*args, env=env, **kwargs)


class BuildrunnerTest(unittest.TestCase):
  """Holds tests for the buildrunner script."""
  def setUp(self):
    super(BuildrunnerTest, self).setUp()

    self.runbuild = os.path.join(SCRIPT_DIR,
                                 '..', 'runbuild.py')
    self.capture = chromium_utils.FilterCapture()
    self.master_dir = os.path.join(SCRIPT_DIR, 'data', 'runbuild_master')

    self.failing_master_dir = os.path.join(SCRIPT_DIR, 'data',
                                           'failing_master')

  def testSampleMaster(self):
    sample = '--master-dir=%s' % self.master_dir
    cmd = [sys.executable, self.runbuild, sample, '--list-builders']
    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)

    self.assertEqual(ret, 0)
    self.assertEqual(self.capture.text[-1].split(' ')[0], 'runtests')

  def testListSteps(self):
    sample = '--master-dir=%s' % self.master_dir
    cmd = [sys.executable, self.runbuild, sample, '--svn-rev=12345',
           'runtests', '--list-steps']
    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)

    self.assertEqual(ret, 0)

    # On Windows, stderr may get mixed in with stdio so we make our
    # tests flexible.
    splits = [l.split(' ') for l in self.capture.text]
    steps = [s[1] for s in splits if len(s) > 1]
    self.assertTrue('run' in steps)
    self.assertTrue('donotrun' in steps)

  def testRunSteps(self):
    sample = '--master-dir=%s' % self.master_dir
    slavedir = '--slave-dir=%s' % self.master_dir
    cmd = [sys.executable, self.runbuild, sample, slavedir, '--svn-rev=12345',
           '--log=-', 'runtests']
    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)

    self.assertEqual(ret, 0)
    self.assertTrue('buildrunner should run this' in self.capture.text)
    self.assertTrue('buildrunner should not run this' not in self.capture.text)

  def testCatchDupSteps(self):
    sample = '--master-dir=%s' % self.failing_master_dir
    cmd = [sys.executable, self.runbuild, sample, 'runtests', '--list-steps']
    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)

    self.assertEqual(ret, 1)


if __name__ == '__main__':
  unittest.main()
