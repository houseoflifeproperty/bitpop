#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0403,W0611

import json
import StringIO
import unittest
import urllib2

from testing_support.super_mox import mox
from testing_support.super_mox import SuperMoxTestBase

import slave.get_swarm_results as swarm_results


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

SWARM_OUTPUT_WITHOUT_FAILURE = ("""
[ RUN      ] unittests.Run Test
""" +
RUN_TEST_OUTPUT +
"""[       OK ] unittests.Run Test (2549 ms)
[ RUN      ] unittests.Clean Up
No output!
[       OK ] unittests.Clean Up (6 ms)

[----------] unittests summary
[==========] 2 tests ran. (2556 ms total)
""")

SWARM_OUTPUT_WITH_FAILURE = ("""
[ RUN      ] unittests.Run Test
""" +
RUN_TEST_OUTPUT_FAILURE +
"""[       OK ] unittests.Run Test (2549 ms)
[ RUN      ] unittests.Clean Up
No output!
[       OK ] unittests.Clean Up (6 ms)

[----------] unittests summary
[==========] 2 tests ran. (2556 ms total)
""")

SWARM_OUTPUT_WITH_NO_TEST_OUTPUT = """
Unable to connection to swarm machine.
"""

BUILDBOT_OUTPUT = ("""
================================================================
Begin output from shard index 0 (machine tag: localhost, id: host)
================================================================

""" + RUN_TEST_OUTPUT +
"""
================================================================
End output from shard index 0 (machine tag: localhost, id: host). Return 0
================================================================

Summary for all the shards:
All tests passed.
""")

BUILDBOT_OUTPUT_FAILURE = ("""
================================================================
Begin output from shard index 0 (machine tag: localhost, id: host)
================================================================

""" + RUN_TEST_OUTPUT_FAILURE +
"""
================================================================
End output from shard index 0 (machine tag: localhost, id: host). Return 1
================================================================

Summary for all the shards:
1 test failed, listed below:
  StaticCookiePolicyTest.BlockAllCookiesTest
""")

BUILDBOT_OUTPUT_NO_TEST_OUTPUT = ("""
================================================================
Begin output from shard index 0 (machine tag: localhost, id: host)
================================================================

No output produced by the test, it may have failed to run.
Showing all the output, including swarm specific output.

""" + SWARM_OUTPUT_WITH_NO_TEST_OUTPUT +
"""
================================================================
End output from shard index 0 (machine tag: localhost, id: host). Return 1
================================================================

Summary for all the shards:
All tests passed.
""")



TEST_SHARD_1 = 'Note: This is test shard 1 of 3.'
TEST_SHARD_2 = 'Note: This is test shard 2 of 3.'
TEST_SHARD_3 = 'Note: This is test shard 3 of 3.'


class TestRunOutputTest(unittest.TestCase):
  def test_correct_output_success(self):
    self.assertEqual(RUN_TEST_OUTPUT,
                     swarm_results.TestRunOutput(SWARM_OUTPUT_WITHOUT_FAILURE))

  def test_correct_output_failure(self):
    self.assertEqual(RUN_TEST_OUTPUT_FAILURE,
                     swarm_results.TestRunOutput(SWARM_OUTPUT_WITH_FAILURE))


class GetTestKetsTest(SuperMoxTestBase):
  def test_no_keys(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    response = StringIO.StringIO('No matching Test Cases')
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        response)
    self.mox.ReplayAll()

    self.assertEqual([], swarm_results.GetTestKeys('http://host:9001',
                                                   'my_test'))
    self.checkstdout('Error: Unable to find any tests with the name, '
                     'my_test, on swarm server\n')

    self.mox.VerifyAll()

  def test_find_keys(self):
    keys = ['key_1', 'key_2']

    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    response = StringIO.StringIO(json.dumps(keys))
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        response)
    self.mox.ReplayAll()

    self.assertEqual(keys,
                     swarm_results.GetTestKeys('http://host:9001', 'my_test'))

    self.mox.VerifyAll()


class AllShardsRun(unittest.TestCase):
  def testAllShardsRun(self):
    shard_watcher = swarm_results.ShardWatcher(3)

    shard_watcher.ProcessLine(TEST_SHARD_1)
    shard_watcher.ProcessLine(TEST_SHARD_2)
    shard_watcher.ProcessLine(TEST_SHARD_3)

    self.assertEqual([], shard_watcher.MissingShards())
    self.assertTrue(shard_watcher.ShardsCompleted())

  def testShardRepeated(self):
    shard_watcher = swarm_results.ShardWatcher(3)

    shard_watcher.ProcessLine(TEST_SHARD_1)
    shard_watcher.ProcessLine(TEST_SHARD_1)
    shard_watcher.ProcessLine(TEST_SHARD_1)

    self.assertEqual(['2', '3'], shard_watcher.MissingShards())
    self.assertFalse(shard_watcher.ShardsCompleted())


class GetSwarmResults(SuperMoxTestBase):
  def test_get_swarm_results_success(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    shard_output = json.dumps(
      {'machine_id': 'host',
       'machine_tag': 'localhost',
       'exit_codes': '0, 0',
       'output': SWARM_OUTPUT_WITHOUT_FAILURE
     }
    )

    url_response = urllib2.addinfourl(StringIO.StringIO(shard_output),
                                      "mock message", 'host')
    url_response.code = 200
    url_response.msg = "OK"
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=key1'
                                  ).AndReturn(url_response)
    swarm_results.urllib2.urlopen('http://host:9001/cleanup_results',
                                  mox.IgnoreArg())
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', ['key1'])

    self.checkstdout(BUILDBOT_OUTPUT)

    self.mox.VerifyAll()

  def test_get_swarm_results_failure(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    shard_output = json.dumps(
      {'machine_id': 'host',
       'machine_tag': 'localhost',
       'exit_codes': '0, 1',
       'output': SWARM_OUTPUT_WITH_FAILURE
     }
    )

    url_response = urllib2.addinfourl(StringIO.StringIO(shard_output),
                                      "mock message", 'host')
    url_response.code = 200
    url_response.msg = "OK"
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=key1'
                                  ).AndReturn(url_response)
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', ['key1'])

    self.checkstdout(BUILDBOT_OUTPUT_FAILURE)

    self.mox.VerifyAll()

  def test_get_swarm_results_no_test_output(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')

    shard_output = json.dumps(
      {'machine_id': 'host',
       'machine_tag': 'localhost',
       'exit_codes': '0, 0',
       'output': SWARM_OUTPUT_WITH_NO_TEST_OUTPUT
     }
    )

    url_response = urllib2.addinfourl(StringIO.StringIO(shard_output),
                                      "mock message", 'host')
    url_response.code = 200
    url_response.msg = "OK"
    swarm_results.urllib2.urlopen('http://host:9001/get_result?r=key1'
                                  ).AndReturn(url_response)
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', ['key1'])

    self.checkstdout(BUILDBOT_OUTPUT_NO_TEST_OUTPUT)

    self.mox.VerifyAll()

  def test_get_swarm_results_no_keys(self):
    swarm_results.GetSwarmResults('http://host:9001', [])

    self.checkstdout('Error: No test keys to get results with\n')

    self.mox.VerifyAll()

  def test_get_swarm_results_url_errors(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    url = 'http://host:9001/get_result?r=key1'
    exception = urllib2.URLError('failed to connect')

    for _ in range(swarm_results.MAX_RETRY_ATTEMPTS):
      swarm_results.urllib2.urlopen(url).AndRaise(exception)
    self.mox.ReplayAll()

    swarm_results.GetSwarmResults('http://host:9001', ['key1'])

    expected_output = []
    for _ in range(swarm_results.MAX_RETRY_ATTEMPTS):
      expected_output.append('Error: Calling %s threw %s' % (url, exception))
    expected_output.append(
        'Unable to connect to the given url, %s, after %d attempts. Aborting.' %
        (url, swarm_results.MAX_RETRY_ATTEMPTS))
    expected_output.append('Summary for all the shards:')
    expected_output.append('All tests passed.')

    self.checkstdout('\n'.join(expected_output) + '\n')

    self.mox.VerifyAll()


if __name__ == '__main__':
  unittest.main()
