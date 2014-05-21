#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/presubmit_check.py."""

import logging
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

from verification import base
from verification import presubmit_check

import find_depot_tools  # pylint: disable=W0611
from testing_support import trial_dir

# From tests/
import mocks


class PresubmitTest(mocks.TestCase, trial_dir.TrialDirMixIn):
  def setUp(self):
    mocks.TestCase.setUp(self)
    trial_dir.TrialDirMixIn.setUp(self)

    # The presubmit check assumes PWD is set accordingly.
    self._old_cwd = os.getcwd()
    os.chdir(self.root_dir)
    with open(os.path.join(self.root_dir, 'hello.txt'), 'wb') as f:
      f.write('allo')
    self.pending.files = ['hello.txt']

  def tearDown(self):
    os.chdir(self._old_cwd)
    trial_dir.TrialDirMixIn.tearDown(self)
    mocks.TestCase.tearDown(self)

  def _presubmit(self, content):
    # Creates the presubmit check.
    with open(os.path.join(self.root_dir, 'PRESUBMIT.py'), 'wb') as f:
      f.write(content)

  def testPresubmitBuggy(self):
    self._presubmit('symbol_not_defined\n')
    self._check(error_message='symbol_not_defined')

  def testPresubmitHangs(self):
    self._presubmit('import time\ntime.sleep(5)')
    self._check(error_message='The presubmit check was hung.', expiration=0.2)

  def testSuccess(self):
    self._presubmit('')
    self._check()

  def testSuccessNotify(self):
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  return [output_api.PresubmitNotifyResult("There is no problem")]\n')
    self._check()

  def testFailWarning(self):
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  return [output_api.PresubmitPromptWarning(\n'
        '      "There is some problems")]\n')
    self._check(error_message='There is some problems\n')

  def testFailError(self):
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  return [output_api.PresubmitError("Die die please die")]\n')
    self._check(error_message='Die die please die')

  def _check(self, error_message=None, expiration=None):
    # checkout is not used yet. To be used to get the list of modified files.
    ver = presubmit_check.PresubmitCheckVerifier(self.context)
    if expiration:
      ver.execution_timeout = expiration
    ver.verify(self.pending)
    ver.update_status(None)
    name = presubmit_check.PresubmitCheckVerifier.name
    self.assertEquals(self.pending.verifications.keys(), [name])
    if error_message:
      self.assertIn(
          error_message, self.pending.verifications[name].error_message)
      self.assertEquals(
          self.pending.verifications[name].get_state(), base.FAILED)
      self.assertIn(error_message, self.pending.error_message())
    else:
      self.assertEquals(None, self.pending.verifications[name].error_message)
      self.assertEquals(
          self.pending.verifications[name].get_state(), base.SUCCEEDED)
      self.assertEquals('', self.pending.error_message())
    self.context.status.check_names(['presubmit'] * 2)

  def testPresubmitTryJob(self):
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  out = input_api.canned_checks.CheckRietveldTryJobExecution(\n'
        '      1, 2, 3, 4, 5, 6, absurd=True)\n'
        '  assert [] == out\n'
        '  return out\n')
    self._check()

  def testPresubmitTreeOpen(self):
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  out = input_api.canned_checks.CheckTreeIsOpen(\n'
        '      1, 2, 3, 4, 5, 6, absurd=True)\n'
        '  assert [] == out\n'
        '  return out\n')
    self._check()

  def testPresubmitPendingBuilds(self):
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  out = input_api.canned_checks.CheckBuildbotPendingBuilds(\n'
        '      1, 2, 3, 4, 5, 6, absurd=True)\n'
        '  assert [] == out\n'
        '  return out\n')
    self._check()

  def testPresubmitRietveld(self):
    self._presubmit(
        ('def CheckChangeOnCommit(input_api, output_api):\n'
          '  out = []\n'
          '  if input_api.rietveld.email != %r:\n'
          '    out.append(output_api.PresubmitError(\n'
          '      "email: %%r" %% input_api.rietveld.email))\n'
          # TODO(maruel): Bad! Remove me.
          '  if input_api.rietveld.password != %r:\n'
          '    out.append(output_api.PresubmitError(\n'
          '      "password: %%r" %% input_api.rietveld.password))\n'
          '  if input_api.rietveld.url != %r:\n'
          '    out.append(output_api.PresubmitError(\n'
          '      "url: %%r" %% input_api.rietveld.url))\n'
          '  return out\n') % (
            self.context.rietveld.email,
            self.context.rietveld.password,
            self.context.rietveld.url))

    self._check()

  def testPresubmitNoFiles(self):
    self.pending.files = []
    self._presubmit(
        'def CheckChangeOnCommit(input_api, output_api):\n'
        '  return []\n')
    # TODO(maruel): Would make sense to have a more helpful error message.
    self._check(
        'Presubmit check for 42-23 failed and returned exit status 2.\n\n'
        'Usage: presubmit_shim.py [options] <files...>\n\n'
        'presubmit_shim.py: error: For unversioned directory, <files> is not '
        'optional.\n')


if __name__ == '__main__':
  if '-v' in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.ERROR)
  unittest.main()
