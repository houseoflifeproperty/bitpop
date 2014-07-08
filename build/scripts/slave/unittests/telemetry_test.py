#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for telemetry.py.

This is a basic check that telemetry.py forms commands properly.

"""

import json
import os
import sys
import unittest

import test_env  # pylint: disable=W0403,W0611

from common import chromium_utils


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def runScript(*args, **kwargs):
  """Ensures scripts have a proper PYTHONPATH."""
  env = os.environ.copy()
  env['PYTHONPATH'] = os.pathsep.join(sys.path)
  return chromium_utils.RunCommand(*args, env=env, **kwargs)


class TelemetryTest(unittest.TestCase):
  """Holds tests for telemetry script."""

  @staticmethod
  def _GetDefaultFactoryProperties():
    fp = {}
    fp['build_dir'] = 'src/out'
    fp['test_name'] = 'sunspider'
    fp['target'] = 'Release'
    fp['target_os'] = 'android'
    fp['target_platform'] = 'linux2'
    fp['step_name'] = 'sunspider'
    fp['show_perf_results'] = True
    fp['perf_id'] = 'android-gn'
    return fp

  def setUp(self):
    super(TelemetryTest, self).setUp()

    self.telemetry = os.path.join(SCRIPT_DIR, '..', 'telemetry.py')
    self.capture = chromium_utils.FilterCapture()

  def testSimpleCommand(self):
    fp = self._GetDefaultFactoryProperties()

    cmd = [self.telemetry, '--print-cmd',
           '--factory-properties=%s' % json.dumps(fp)]

    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)
    self.assertEqual(ret, 0)

    runtest = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'runtest.py'))

    expectedText = ([
        '\'%s\' ' % sys.executable +
        '\'%s\' \'--run-python-script\' \'--target\' \'Release\' ' % runtest +
            '\'--no-xvfb\' ' +
            '\'--factory-properties=' +
            '{"target": "Release", ' +
            '"build_dir": "src/out", "perf_id": "android-gn", ' +
            '"step_name": "sunspider", "test_name": "sunspider", ' +
            '"target_platform": "linux2", "target_os": "android", ' +
            '"show_perf_results": true}\' ' +
            '\'src/build/android/test_runner.py\' \'perf\' \'-v\' ' +
            '\'--release\' ' +
            '\'--single-step\' ' +
            '\'--\' ' +
            '\'src/tools/perf/run_benchmark\' \'-v\' ' +
            '\'--output-format=buildbot\' ' +
            '\'--report-root-metrics\' ' +
            '\'--browser=android-chromium-testshell\' \'sunspider\''
        ])

    self.assertEqual(expectedText, self.capture.text)

  def testExtraArg(self):
    fp = self._GetDefaultFactoryProperties()
    fp['extra_args'] = ['--profile-dir=fake_dir']

    cmd = [self.telemetry, '--print-cmd',
           '--factory-properties=%s' % json.dumps(fp)]

    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)
    self.assertEqual(ret, 0)

    runtest = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'runtest.py'))

    expectedText = ([
        '\'%s\' ' % sys.executable +
        '\'%s\' \'--run-python-script\' \'--target\' \'Release\' ' % runtest +
            '\'--no-xvfb\' ' +
            '\'--factory-properties=' +
            '{"target": "Release", "build_dir": "src/out", ' +
            '"extra_args": ["--profile-dir=fake_dir"], ' +
            '"perf_id": "android-gn", ' +
            '"step_name": "sunspider", "test_name": "sunspider", ' +
            '"target_platform": "linux2", "target_os": "android", ' +
            '"show_perf_results": true}\' ' +
            '\'src/build/android/test_runner.py\' \'perf\' \'-v\' ' +
            '\'--release\' ' +
            '\'--single-step\' ' +
            '\'--\' ' +
            '\'src/tools/perf/run_benchmark\' \'-v\' ' +
            '\'--output-format=buildbot\' ' +
            '\'--report-root-metrics\' ' +
            '\'--profile-dir=fake_dir\' '+
            '\'--browser=android-chromium-testshell\' \'sunspider\''
        ])

    self.assertEqual(expectedText, self.capture.text)

if __name__ == '__main__':
  unittest.main()
