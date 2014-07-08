#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import sys
import unittest

import test_env  # pylint: disable=W0403,W0611


# Create a fake swarm_get_results module.
class FakeSwarmGetResultsModule(object):
  @staticmethod
  def yield_results(url, keys, timeout, max_threads):
    raise NotImplementedError()

  @staticmethod
  def parse_args():
    raise NotImplementedError()

  @staticmethod
  def get_test_keys(url, test_name):
    raise NotImplementedError()


sys.modules['swarm_get_results'] = FakeSwarmGetResultsModule()


import slave.swarming.get_swarm_results_shim as swarm_results


RUN_TEST_OUTPUT = (
"""[----------] 2 tests from StaticCookiePolicyTest
[ RUN      ] StaticCookiePolicyTest.AllowAllCookiesTest
[       OK ] StaticCookiePolicyTest.AllowAllCookiesTest (0 ms)
[ RUN      ] StaticCookiePolicyTest.BlockAllCookiesTest
[       OK ] StaticCookiePolicyTest.BlockAllCookiesTest (0 ms)
[----------] 2 tests from StaticCookiePolicyTest (0 ms total)

[----------] 1 test from TCPListenSocketTest
[ RUN      ] TCPListenSocketTest.ServerSend
[       OK ] TCPListenSocketTest.ServerSend (1 ms)
[----------] 1 test from TCPListenSocketTest (1 ms total)
""")

RUN_TEST_OUTPUT_FAILURE = (
"""[----------] 2 tests from StaticCookiePolicyTest
[ RUN      ] StaticCookiePolicyTest.AllowAllCookiesTest
[       OK ] StaticCookiePolicyTest.AllowAllCookiesTest (0 ms)
[ RUN      ] StaticCookiePolicyTest.BlockAllCookiesTest
E:\b\build\slave\win\build\src\chrome\test.cc: error: Value of: result()
  Actual: false
Expected: true
[  FAILED  ] StaticCookiePolicyTest.BlockAllCookiesTest (0 ms)
[----------] 2 tests from StaticCookiePolicyTest (0 ms total)

[----------] 1 test from TCPListenSocketTest
[ RUN      ] TCPListenSocketTest.ServerSend
[       OK ] TCPListenSocketTest.ServerSend (1 ms)
[----------] 1 test from TCPListenSocketTest (1 ms total)
""")


BUILDBOT_OUTPUT_FMT = """
================================================================
Begin output from shard index %d (machine tag: localhost, id: host)
================================================================

%s
================================================================
End output from shard index %d (machine tag: localhost, id: host). Return %d
================================================================
"""


def generate_swarm_response(index, shard_output, exit_codes):
  return {
    u'config_instance_index': index,
    u'exit_codes': exit_codes,
    u'machine_id': 'host',
    u'machine_tag': 'localhost',
    u'num_config_instances': 1,
    u'output': shard_output,
  }


class FakeGtestParser(object):
  @staticmethod
  def ProcessLine(*args, **kwargs):
    pass


class TestOutputTest(unittest.TestCase):
  def test_shard_output_success(self):
    expected = BUILDBOT_OUTPUT_FMT % (0, RUN_TEST_OUTPUT, 0, 0)
    result = generate_swarm_response(0, RUN_TEST_OUTPUT, '0')
    actual = swarm_results.gen_shard_output(result, FakeGtestParser())
    self.assertEqual((expected, 0), actual)

  def test_shard_output_failure(self):
    expected = BUILDBOT_OUTPUT_FMT % (0, RUN_TEST_OUTPUT_FAILURE, 0, 1)
    result = generate_swarm_response(0, RUN_TEST_OUTPUT_FAILURE, '1')
    actual = swarm_results.gen_shard_output(result, FakeGtestParser())
    self.assertEqual((expected, 1), actual)

  def test_shard_output_empty(self):
    expected = BUILDBOT_OUTPUT_FMT % (0, swarm_results.NO_OUTPUT_FOUND, 0, 1)
    result = generate_swarm_response(0, '', '0')
    actual = swarm_results.gen_shard_output(result, FakeGtestParser())
    self.assertEqual((expected, 1), actual)


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.ERROR)
  if '-v' in sys.argv:
    unittest.TestCase.maxDiff = None
  unittest.main()
