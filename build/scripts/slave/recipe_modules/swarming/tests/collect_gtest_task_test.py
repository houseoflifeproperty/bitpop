#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cStringIO
import json
import logging
import os
import shutil
import sys
import tempfile
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# For 'test_env'.
sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', '..', '..', 'unittests')))
# For 'collect_gtest_task.py'.
sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', 'resources')))

# Imported for side effects on sys.path.
import test_env

# In depot_tools/
from testing_support import auto_stub
import collect_gtest_task


# gtest json output for successfully finished shard #0.
GOOD_GTEST_JSON_0 = {
  'all_tests': [
    'AlignedMemoryTest.DynamicAllocation',
    'AlignedMemoryTest.ScopedDynamicAllocation',
    'AlignedMemoryTest.StackAlignment',
    'AlignedMemoryTest.StaticAlignment',
  ],
  'disabled_tests': [
    'ConditionVariableTest.TimeoutAcrossSetTimeOfDay',
    'FileTest.TouchGetInfo',
    'MessageLoopTestTypeDefault.EnsureDeletion',
  ],
  'global_tags': ['CPU_64_BITS', 'MODE_DEBUG', 'OS_LINUX', 'OS_POSIX'],
  'per_iteration_data': [{
    'AlignedMemoryTest.DynamicAllocation': [{
      'elapsed_time_ms': 0,
      'losless_snippet': True,
      'output_snippet': 'blah\\n',
      'output_snippet_base64': 'YmxhaAo=',
      'status': 'SUCCESS',
    }],
    'AlignedMemoryTest.ScopedDynamicAllocation': [{
      'elapsed_time_ms': 0,
      'losless_snippet': True,
      'output_snippet': 'blah\\n',
      'output_snippet_base64': 'YmxhaAo=',
      'status': 'SUCCESS',
    }],
  }],
}


# gtest json output for successfully finished shard #1.
GOOD_GTEST_JSON_1 = {
  'all_tests': [
    'AlignedMemoryTest.DynamicAllocation',
    'AlignedMemoryTest.ScopedDynamicAllocation',
    'AlignedMemoryTest.StackAlignment',
    'AlignedMemoryTest.StaticAlignment',
  ],
  'disabled_tests': [
    'ConditionVariableTest.TimeoutAcrossSetTimeOfDay',
    'FileTest.TouchGetInfo',
    'MessageLoopTestTypeDefault.EnsureDeletion',
  ],
  'global_tags': ['CPU_64_BITS', 'MODE_DEBUG', 'OS_LINUX', 'OS_POSIX'],
  'per_iteration_data': [{
    'AlignedMemoryTest.StackAlignment': [{
      'elapsed_time_ms': 0,
      'losless_snippet': True,
      'output_snippet': 'blah\\n',
      'output_snippet_base64': 'YmxhaAo=',
      'status': 'SUCCESS',
    }],
    'AlignedMemoryTest.StaticAlignment': [{
      'elapsed_time_ms': 0,
      'losless_snippet': True,
      'output_snippet': 'blah\\n',
      'output_snippet_base64': 'YmxhaAo=',
      'status': 'SUCCESS',
    }],
  }],
}


class MainFuncTest(auto_stub.TestCase):
  """Tests for 'main' function."""

  def setUp(self):
    super(MainFuncTest, self).setUp()

    # Temp root dir for the test.
    self.temp_dir = tempfile.mkdtemp()

    # Collect calls to 'subprocess.call'.
    self.subprocess_calls = []
    def mocked_subprocess_call(args):
      self.subprocess_calls.append(args)
      return 0
    self.mock(
        collect_gtest_task.subprocess,
        'call',
        mocked_subprocess_call)

    # Collect number of calls to 'process_gtest_json_output'.
    self.process_output_calls = 0
    def mocked_process_gtest_json_output(_exit_code, _task_output_dir):
      self.process_output_calls += 1
    self.mock(
        collect_gtest_task,
        'process_gtest_json_output',
        mocked_process_gtest_json_output)

    # Make tempfile.mkdtemp deterministic.
    self.mkdtemp_counter = 0
    def fake_mkdtemp(prefix=None, suffix=None, dir=None):
      self.mkdtemp_counter += 1
      return self.mkdtemp_result(self.mkdtemp_counter, prefix, suffix, dir)
    self.mock(
        collect_gtest_task.tempfile,
        'mkdtemp',
        fake_mkdtemp)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)
    super(MainFuncTest, self).tearDown()

  def mkdtemp_result(self, index, prefix=None, suffix=None, dir=None):
    """Result of fake mkdtemp call for given invocation index."""
    return os.path.join(
        dir or self.temp_dir,
        '%s%d%s' % (prefix or '', index, suffix or ''))

  def test_main_calls_swarming_py_no_extra_args(self):
    exit_code = collect_gtest_task.main([
      '--swarming-client-dir', os.path.join(self.temp_dir, 'fake_swarming'),
      '--temp-root-dir', self.temp_dir,
      '--',
      'positional0',
      '--swarming-arg0', '0'
      '--swarming-arg1', '1',
      'positional1',
    ])
    self.assertEqual(0, exit_code)

    # Should append correct --task-output-dir to args after '--'.
    self.assertEqual(
        [[
          sys.executable,
          '-u',
          os.path.join(self.temp_dir, 'fake_swarming', 'swarming.py'),
          'positional0',
          '--swarming-arg0', '0'
          '--swarming-arg1', '1',
          'positional1',
          '--task-output-dir',
          self.mkdtemp_result(1, suffix='_swarming', dir=self.temp_dir),
        ]],
        self.subprocess_calls)
    self.assertEqual(1, self.process_output_calls)

  def test_main_calls_swarming_py_with_extra_args(self):
    exit_code = collect_gtest_task.main([
      '--swarming-client-dir', os.path.join(self.temp_dir, 'fake_swarming'),
      '--temp-root-dir', self.temp_dir,
      '--',
      'positional0',
      '--swarming-arg0', '0'
      '--swarming-arg1', '1',
      'positional1',
      '--',
      '--isolated-cmd-extra-arg0',
      'extra_arg1',
    ])
    self.assertEqual(0, exit_code)

    # Should insert correct --task-output-dir before extra args to swarming.py.
    self.assertEqual(
        [[
          sys.executable,
          '-u',
          os.path.join(self.temp_dir, 'fake_swarming', 'swarming.py'),
          'positional0',
          '--swarming-arg0', '0'
          '--swarming-arg1', '1',
          'positional1',
          '--task-output-dir',
          self.mkdtemp_result(1, suffix='_swarming', dir=self.temp_dir),
          '--',
          '--isolated-cmd-extra-arg0',
          'extra_arg1',
        ]],
        self.subprocess_calls)
    self.assertEqual(1, self.process_output_calls)


class CollectGTestTaskTest(auto_stub.TestCase):
  """Tests for process_gtest_json_output function."""

  def setUp(self):
    super(CollectGTestTaskTest, self).setUp()
    self.temp_dir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.temp_dir)
    super(CollectGTestTaskTest, self).tearDown()

  def stage(self, files):
    for path, content in files.iteritems():
      abs_path = os.path.join(self.temp_dir, path.replace('/', os.sep))
      if not os.path.exists(os.path.dirname(abs_path)):
        os.makedirs(os.path.dirname(abs_path))
      with open(abs_path, 'w') as f:
        if isinstance(content, dict):
          json.dump(content, f)
        else:
          assert isinstance(content, str)
          f.write(content)

  def call(self, exit_code=0):
    stdout = cStringIO.StringIO()
    self.mock(sys, 'stdout', stdout)
    collect_gtest_task.process_gtest_json_output(exit_code, self.temp_dir)
    return stdout.getvalue().strip()

  def test_ok(self):
    # Two shards, both successfully finished.
    self.stage({
      'summary.json': {'shards': [{'dummy': 0}, {'dummy': 0}]},
      '0/output.json': GOOD_GTEST_JSON_0,
      '1/output.json': GOOD_GTEST_JSON_1,
    })
    self.assertEqual(
        'exit code (as seen by runtest.py): 0\n'
        '@@@STEP_TEXT@@@@\n'
        '@@@STEP_TEXT@3 disabled@@@',
        self.call())

  def test_missing_summary_json(self):
    # summary.json is missing, should emit warning.
    output = self.call()
    self.assertIn('@@@STEP_WARNINGS@@@', output)
    self.assertIn('summary.json is missing or can not be read', output)

  def test_unfinished_shards(self):
    # Only one shard (#1) finished. Shard #0 did not.
    self.stage({
      'summary.json': {'shards': [None, {'dummy': 0}]},
      '1/output.json': GOOD_GTEST_JSON_1,
    })
    self.assertEqual(
        '@@@STEP_WARNINGS@@@\n'
        'missing results from some shards\n'
        '@@@STEP_LOG_LINE@missing results from some shards@'
        'Missing results from the following shard(s): 0@@@\n'
        '@@@STEP_LOG_END@missing results from some shards@@@\n'
        'exit code (as seen by runtest.py): 1\n'
        '@@@STEP_FAILURE@@@\n'
        '@@@STEP_TEXT@@@@\n'
        '@@@STEP_TEXT@3 disabled@@@\n'
        '@@@STEP_TEXT@crashed or hung@@@',
        self.call(1))


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.ERROR)
  if '-v' in sys.argv:
    unittest.TestCase.maxDiff = None
  unittest.main()
