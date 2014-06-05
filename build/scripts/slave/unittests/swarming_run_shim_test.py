#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import Queue
import StringIO
import json
import logging
import sys
import threading
import unittest

import test_env  # pylint: disable=W0403,W0611

# In depot_tools/
from testing_support import auto_stub

from slave.swarming import swarming_run_shim


# pylint: disable=W0212


class StateMachine(object):
  """State machine to coordinate steps accross multiple threads."""
  def __init__(self):
    self._step = 0
    self.condition = threading.Condition()

  def increment(self):
    with self.condition:
      self._step += 1
      logging.info('Switching machine to step %d', self._step)
      self.condition.notify_all()

  def wait_for(self, value):
    while True:
      with self.condition:
        if self._step == value:
          return


class SwarmingRunTest(auto_stub.TestCase):
  def test_stream(self):
    cmd = [
        sys.executable,
        '-c',
        'import time; print("a"); time.sleep(0.1); print("b")',
    ]
    actual = list(swarming_run_shim.stream_process(cmd))
    self.assertEqual(['a\n', 'b\n', 0], actual)

  def test_none(self):
    def stream_process_mock(cmd):
      self.fail()

    def find_client_mock(path):
      return '/doesn\'t/exist/'

    self.mock(swarming_run_shim, 'stream_process', stream_process_mock)
    self.mock(swarming_run_shim.swarming_utils, 'find_client', find_client_mock)
    self.mock(swarming_run_shim.swarming_utils, 'get_version', lambda _: (0, 4))
    self.mock(sys, 'stdout', StringIO.StringIO())

    cmd = [
        '--swarming', 'http://localhost:1',
        '--isolate-server', 'http://localhost:2',
    ]
    props = {
        'target_os': 'darwin',
        'buildbotURL': 'http://build.chromium.org/p/chromium.win/'
    }
    cmd.extend(('--build-properties', json.dumps(props)))
    self.assertEqual(0, swarming_run_shim.main(cmd))
    expected = 'Nothing to trigger\n\n@@@STEP_WARNINGS@@@\n'
    self.assertEqual(expected, sys.stdout.getvalue())

  def test_one(self):
    cmds = []
    def stream_process_mock(cmd):
      cmds.append(cmd)
      yield 'a\n'
      yield 'b\n'
      yield 'c\n'
      yield 0

    def find_client_mock(path):
      return '/doesn\'t/exist/'

    self.mock(swarming_run_shim, 'stream_process', stream_process_mock)
    self.mock(swarming_run_shim.swarming_utils, 'find_client', find_client_mock)
    self.mock(swarming_run_shim.swarming_utils, 'get_version', lambda _: (0, 4))
    self.mock(sys, 'stdout', StringIO.StringIO())

    cmd = [
        '--swarming', 'http://localhost:1',
        '--isolate-server', 'http://localhost:2',
    ]
    props = {
        'buildername': 'win_rel',
        'buildnumber': 18,
        'buildbotURL': 'http://build.chromium.org/p/chromium.win/',
        'swarm_hashes': {'base_test': '1234'},
        'target_os': 'darwin',
        'testfilter': ['base_test_swarm'],
    }
    cmd.extend(('--build-properties', json.dumps(props)))
    self.assertEqual(0, swarming_run_shim.main(cmd))
    expected_cmd = [
        sys.executable,
        "/doesn't/exist/swarming.py",
        'run',
        '--swarming', 'http://localhost:1',
        '--isolate-server', 'http://localhost:2',
        '--priority', '10',
        '--shards', '1',
        '--task-name', u'base_test/Mac/1234/win_rel/18',
        '--decorate',
        u'1234',
        '--dimension', 'os', 'Mac',
    ]
    self.assertEqual([expected_cmd], cmds)
    expected = (
        'Selected tests:\n base_test\nSelected OS: Mac\n'
        '\n@@@SEED_STEP base_test@@@\n'
        '\n@@@STEP_CURSOR base_test@@@\n'
        '\n@@@STEP_STARTED@@@\n'
        '\n@@@STEP_TEXT@Mac@@@\n'
        '\n@@@STEP_TEXT@1234@@@\n'
        'a\nb\nc\n'
        '\n@@@STEP_CLOSED@@@\n'
        '\n'
    )
    self.assertEqual(expected, sys.stdout.getvalue())

  def test_default(self):
    def stream_process_mock(cmd):
      yield 'a\n'
      yield 0
    self.mock(swarming_run_shim, 'stream_process', stream_process_mock)
    self.mock(swarming_run_shim.swarming_utils, 'find_client', lambda _: '/a')
    self.mock(swarming_run_shim.swarming_utils, 'get_version', lambda _: (0, 4))
    self.mock(sys, 'stdout', StringIO.StringIO())

    cmd = [
        '--swarming', 'http://localhost:1',
        '--isolate-server', 'http://localhost:2',
    ]
    # Not a try server, missing most build properties.
    props = {
        'swarm_hashes': {'base_test': '1234'},
    }
    cmd.extend(('--build-properties', json.dumps(props)))
    self.assertEqual(0, swarming_run_shim.main(cmd))
    expected = (
        'Selected tests:\n base_test\nSelected OS: %(OS)s\n'
        '\n@@@SEED_STEP base_test@@@\n'
        '\n@@@STEP_CURSOR base_test@@@\n'
        '\n@@@STEP_STARTED@@@\n'
        '\n@@@STEP_TEXT@%(OS)s@@@\n'
        '\n@@@STEP_TEXT@1234@@@\n'
        'a\n'
        '\n@@@STEP_CLOSED@@@\n'
        '\n'
    ) % {'OS': swarming_run_shim.swarming_utils.OS_MAPPING[sys.platform]}
    self.assertEqual(expected, sys.stdout.getvalue())

  def test_three(self):
    out = Queue.Queue()
    def drive_many(*args, **kwargs):
      # Inject our own queue.
      return swarming_run_shim._drive_many(*args, out=out, **kwargs)
    self.mock(swarming_run_shim, 'drive_many', drive_many)

    lock = threading.Lock()
    cmds = set()
    step = StateMachine()
    def stream_process_mock(cmd):
      """The unlocking pattern is:
        0. base_test outputs 2 lines and complete.
        1. slow_test outputs 1 line
        2. bloa_test outputs 1 line
        3. slow_test outputs 1 line
        4. bloa_test outputs 1 line
        5. slow_test complete
        6. bloa_test complete
      """
      with lock:
        cmds.add(tuple(cmd))
      if 'base_test/Mac/1234/win_rel/18' in cmd:
        step.wait_for(0)
        yield 'base1\n'
        out.join()
        yield 'base2\n'
        out.join()
        yield 0
        out.join()
        step.increment()
      elif 'slow_test/Mac/4321/win_rel/18' in cmd:
        step.wait_for(1)
        yield 'slow1\n'
        out.join()
        step.increment()

        step.wait_for(3)
        yield 'slow2\n'
        out.join()
        step.increment()

        step.wait_for(5)
        yield 1
        out.join()
        step.increment()
      elif 'bloa_test/Mac/0000/win_rel/18' in cmd:
        step.wait_for(2)
        yield 'bloated1\n'
        out.join()
        step.increment()

        step.wait_for(4)
        yield 'bloated2\n'
        out.join()
        yield 'bloated3\n'
        out.join()
        step.increment()

        step.wait_for(6)
        yield 0
        out.join()
        step.increment()
      else:
        logging.info('OOOPS')
        self.fail()

    def find_client_mock(path):
      return '/doesn\'t/exist/'

    self.mock(swarming_run_shim, 'stream_process', stream_process_mock)
    self.mock(swarming_run_shim.swarming_utils, 'find_client', find_client_mock)
    self.mock(swarming_run_shim.swarming_utils, 'get_version', lambda _: (0, 4))
    self.mock(sys, 'stdout', StringIO.StringIO())

    cmd = [
        '--swarming', 'http://localhost:1',
        '--isolate-server', 'http://localhost:2',
    ]
    props = {
        'buildername': 'win_rel',
        'buildnumber': 18,
        'swarm_hashes': {
            'base_test': '1234',
            'bloa_test': '0000',
            'slow_test': '4321',
        },
        'target_os': 'darwin',
        'testfilter': ['defaulttests', 'bloa_test_swarm'],
    }
    cmd.extend(('--build-properties', json.dumps(props)))
    self.assertEqual(0, swarming_run_shim.main(cmd))
    expected_cmds = set([
        (
          sys.executable,
          "/doesn't/exist/swarming.py",
          'run',
          '--swarming', 'http://localhost:1',
          '--isolate-server', 'http://localhost:2',
          '--priority', '200',
          '--shards', '1',
          '--task-name', u'base_test/Mac/1234/win_rel/18',
          '--decorate',
          u'1234',
          '--dimension', 'os', 'Mac',
        ),
        (
          sys.executable,
          "/doesn't/exist/swarming.py",
          'run',
          '--swarming', 'http://localhost:1',
          '--isolate-server', 'http://localhost:2',
          '--priority', '200',
          '--shards', '1',
          '--task-name', u'slow_test/Mac/4321/win_rel/18',
          '--decorate',
          u'4321',
          '--dimension', 'os', 'Mac',
        ),
        (
          sys.executable,
          "/doesn't/exist/swarming.py",
          'run',
          '--swarming', 'http://localhost:1',
          '--isolate-server', 'http://localhost:2',
          '--priority', '200',
          '--shards', '1',
          '--task-name', u'bloa_test/Mac/0000/win_rel/18',
          '--decorate',
          u'0000',
          '--dimension', 'os', 'Mac',
        ),
    ])
    self.assertEqual(expected_cmds, cmds)
    actual = sys.stdout.getvalue()
    header = (
        'Selected tests:\n base_test\n bloa_test\n slow_test\n'
        'Selected OS: Mac\n')
    self.assertEqual(header, actual[:len(header)])
    actual = actual[len(header):]
    # Sadly, master/chromium_step.py AnnotationObserver is hard to extract so
    # we have to parse manually.
    expected = (
        u'\n@@@SEED_STEP base_test@@@\n'
        u'\n@@@SEED_STEP bloa_test@@@\n'
        u'\n@@@SEED_STEP slow_test@@@\n'
        u'\n@@@STEP_CURSOR base_test@@@\n'
        u'\n@@@STEP_STARTED@@@\n'
        u'\n@@@STEP_TEXT@Mac@@@\n'
        u'\n@@@STEP_TEXT@1234@@@\n'
        u'\n@@@STEP_CURSOR bloa_test@@@\n'
        u'\n@@@STEP_STARTED@@@\n'
        u'\n@@@STEP_TEXT@Mac@@@\n'
        u'\n@@@STEP_TEXT@0000@@@\n'
        u'\n@@@STEP_CURSOR slow_test@@@\n'
        u'\n@@@STEP_STARTED@@@\n'
        u'\n@@@STEP_TEXT@Mac@@@\n'
        u'\n@@@STEP_TEXT@4321@@@\n'
        u'\n@@@STEP_CURSOR base_test@@@\n'
        u'\n'
        u'base1\nbase2\n'
        u'\n@@@STEP_CLOSED@@@\n'
        u'\n'
        u'\n@@@STEP_CURSOR slow_test@@@\n'
        u'\n'
        u'slow1\n'
        u'\n@@@STEP_CURSOR bloa_test@@@\n'
        u'\n'
        u'bloated1\n'
        u'\n@@@STEP_CURSOR slow_test@@@\n'
        u'\n'
        u'slow2\n'
        u'\n@@@STEP_CURSOR bloa_test@@@\n'
        u'\n'
        u'bloated2\n'
        u'bloated3\n'
        u'\n@@@STEP_CURSOR slow_test@@@\n'
        u'\n'
        u'\n@@@STEP_FAILURE@@@\n'
        u'\n@@@STEP_CLOSED@@@\n'
        u'\n'
        u'\n@@@STEP_CURSOR bloa_test@@@\n'
        u'\n'
        u'\n@@@STEP_CLOSED@@@\n'
        u'\n'
    )
    self.assertEqual(expected.splitlines(), actual.splitlines())


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.ERROR)
  if '-v' in sys.argv:
    unittest.TestCase.maxDiff = None
  unittest.main()
