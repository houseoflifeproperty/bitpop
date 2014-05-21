#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/try_job_on_rietveld.py."""

import logging
import os
import random
import string
import sys
import time
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

# In tests/
import mocks
from mocks import BuildbotMock, BuildbotBuildStep

# In root
from verification import base
from verification import try_job_on_rietveld


def _posted(builders):
  return 'trigger_try_jobs(42, 23, \'CQ\', False, \'HEAD\', %s)' % str(builders)


def gen_job_pending(**kwargs):
  value = {
    '__persistent_type__': 'RietveldTryJobPending',
    'builder': None,
    'clobber': False,
    'init_time': 1.,
    'requested_steps': [],
    'revision': None,
    'tries': 1,
  }
  assert all(arg in value for arg in kwargs)
  value.update(kwargs)
  return value


def gen_job(**kwargs):
  value = {
    '__persistent_type__': 'RietveldTryJob',
    'build': None,
    'builder': None,
    'clobber': False,
    'completed': False,
    'init_time': 1.,
    'requested_steps': [],
    'revision': None,
    'started': 1,
    'steps_failed': [],
    'steps_passed': [],
    'tries': 1,
    'parent_key': None,
  }
  assert all(arg in value for arg in kwargs)
  value.update(kwargs)
  return value


def gen_jobs(**kwargs):
  value =  {
    '__persistent_type__': 'RietveldTryJobs',
    'builders_and_tests': {},
    'triggered_builders': {},
    'error_message': None,
    'irrelevant': [],
    'pendings': [],
    'skipped': False,
    'try_jobs': {},
  }
  assert all(arg in value for arg in kwargs)
  value.update(kwargs)
  return value


class TryJobOnRietveldTest(mocks.TestCase):
  def setUp(self):
    super(TryJobOnRietveldTest, self).setUp()

    # time is requested in the object construction below and self.timestamp
    # will be empty at the end of this function call.
    self.timestamp = [1.]
    self.mock(time, 'time', self._time)

    self.email = 'user1@example.com'
    self.user = 'user1'
    self.builders_and_tests = {
      'linux': ['test1', 'test2'],
      'mac': ['test1', 'test2'],
    }
    self.try_runner = try_job_on_rietveld.TryRunnerRietveld(
        self.context,
        'http://foo/bar',
        self.email,
        self.builders_and_tests,
        [],
        ['ignored_step'],
        'sol',
        )
    # Patch it a little.
    self.try_runner.status = BuildbotMock(self)
    self.try_runner.update_latency = 0

    self.pending.revision = 123

    # It's what rietveld is going to report.
    self._key = (self.pending.issue, self.pending.patchset)
    self.context.rietveld.patchsets_properties[self._key] = {
      'try_job_results': [],
    }

  def tearDown(self):
    self.assertEqual(0, len(self.timestamp))
    self.try_runner.status.check_calls([])
    super(TryJobOnRietveldTest, self).tearDown()

  def _time(self):
    self.assertTrue(self.timestamp)
    return self.timestamp.pop(0)

  def _get_verif(self):
    return self.pending.verifications[self.try_runner.name]

  def _assert_pending_is_empty(self):
    actual = self._get_verif().as_dict()
    expected =  gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=[
        gen_job_pending(builder=u'linux', requested_steps=['test1', 'test2']),
        gen_job_pending(builder=u'mac', requested_steps=['test1', 'test2']),
      ])
    self.assertEqual(expected, actual)

  def _add_build(self, builder, buildnumber, revision, steps, completed):
    """Adds a build with a randomly generated key.

    Adds the build to both the try server and to Rietveld.
    """
    key = ''.join(random.choice(string.ascii_letters) for _ in xrange(8))
    build = self.try_runner.status.add_build(
        builder, buildnumber, revision, key, completed)
    build.steps.extend(steps)
    self.context.rietveld.patchsets_properties[self._key][
        'try_job_results'].append(
          {
            'key': key,
            'builder': builder,
            'buildnumber': buildnumber,
          })
    return key

  def testVoid(self):
    self.assertEqual(self.pending.verifications.keys(), [])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVoidUpdate(self):
    self.try_runner.update_status([])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationVoid(self):
    self.timestamp = [1.] * 6
    self.try_runner.verify(self.pending)
    self._assert_pending_is_empty()
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationUpdateNoJob(self):
    self.timestamp = [1.] * 9
    self.try_runner.verify(self.pending)
    self._assert_pending_is_empty()
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])
    self.try_runner.update_status([self.pending])
    self._assert_pending_is_empty()
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationUpdate(self):
    self.timestamp = [1.] * 11
    self.try_runner.verify(self.pending)
    self._assert_pending_is_empty()
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])
    key = self._add_build('mac', 32, 42, [], False)

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=[
        gen_job_pending(builder='linux', requested_steps=['test1', 'test2']),
      ],
      try_jobs={
        key: gen_job(
          builder='mac',
          build=32,
          requested_steps=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.context.status.check_names(['try job rietveld'] * 1)
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationSuccess(self):
    self.timestamp = [1.] * 13
    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      try_jobs={
        key1: gen_job(
          builder='mac',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.context.status.check_names(['try job rietveld'] * 2)
    self.assertEqual(base.SUCCEEDED, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationRetrySuccess(self):
    self.timestamp = [1.] * 24
    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', False)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=[
        gen_job_pending(builder='mac', requested_steps=['test2'], tries=2),
      ],
      try_jobs={
        key1: gen_job(
          builder='mac',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.context.status.check_names(['try job rietveld'] * 3)
    self.context.rietveld.check_calls(
        [
          _posted({"mac": ["test2"]}),
        ])
    self.assertEqual(base.PROCESSING, self.pending.get_state())

    # Add a new build on mac where test2 passed.
    key3 = self._add_build(
        'mac', 33, 42,
        [BuildbotBuildStep('test1', False), BuildbotBuildStep('test2', True)],
        False)
    self.try_runner.update_status([self.pending])
    self.context.status.check_names(['try job rietveld'] * 1)
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          revision=42,
          steps_passed=['test1', 'test2']),
        key3: gen_job(
          builder='mac',
          build=33,
          requested_steps=['test2'],
          revision=42,
          steps_failed=['test1'],
          steps_passed=['test2'],
          tries=2),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.assertEqual(base.SUCCEEDED, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationRetryRetry(self):
    self.timestamp = [1.] * 37
    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', False)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=[
        gen_job_pending(builder='mac', requested_steps=['test2'], tries=2),
      ],
      try_jobs={
        key1: gen_job(
          builder='mac',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.context.status.check_names(['try job rietveld'] * 3)
    self.context.rietveld.check_calls(
        [
          _posted({"mac": ["test2"]}),
        ])
    self.assertEqual(base.PROCESSING, self.pending.get_state())

    # Add a new build on mac where test2 failed.
    key3 = self._add_build('mac', 33, 42, [BuildbotBuildStep('test2', False)],
                           False)

    self.try_runner.update_status([self.pending])
    self.context.status.check_names(['try job rietveld'] * 2)
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=[
        gen_job_pending(builder='mac', requested_steps=['test2'], tries=3),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          revision=42,
          steps_passed=['test1', 'test2']),
        key3: gen_job(
          builder='mac',
          build=33,
          requested_steps=['test2'],
          revision=42,
          steps_failed=['test2'],
          tries=2),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.context.rietveld.check_calls(
        [
          _posted({"mac": ["test2"]}),
        ])

    # Add a new build on mac where test2 failed again! Too bad now.
    self._add_build('mac', 34, 42, [BuildbotBuildStep('test2', False)],
                    False)

    self.try_runner.update_status([self.pending])
    self.context.status.check_names(['try job rietveld'] * 1)
    self.assertEqual(base.FAILED, self.pending.get_state())
    self.assertEqual(
        'Retried try job too often on mac for step(s) test2',
        self.pending.error_message())

  def testVerificationPreviousJobGood(self):
    self.timestamp = [1.] * 11
    # Reuse the previous job if good.
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'] * 1)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
        ])

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=[
        gen_job_pending(builder='linux', requested_steps=['test1', 'test2']),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_passed=['test1', 'test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0),
        })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def _expired(self, **kwargs):
    # Exacly like testVerificationPreviousJobGood except that jobs are always
    # too old, either by revision or by timestamp.
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'] * 2)
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1", "test2"]}),
          _posted({"mac": ["test1", "test2"]}),
        ])

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      irrelevant=[key1],
      pendings=[
        gen_job_pending(
            builder='linux', requested_steps=['test1', 'test2'], **kwargs),
        gen_job_pending(
            builder='mac', requested_steps=['test1', 'test2'], **kwargs),
      ])
    self.assertEqual(expected, self._get_verif().as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationPreviousExpiredRevisionTooOld(self):
    self.timestamp = [1.] * 10
    self.context.checkout.revisions = lambda _r1, _r2: 201
    self._expired()

  def testVerificationPreviousExpiredDateTooOld(self):
    # 5 days old.
    old = 5*24*60*60.
    self.timestamp = [old] * 10
    self._expired(init_time=old)

  def _previous_job_partially_good(self, steps, steps_failed, completed,
                                   expect_mac_retry):
    # Reuse the previous job tests that passed.
    key1 = self._add_build('mac', 32, 42, steps, completed)

    self.try_runner.verify(self.pending)

    expected_calls = [_posted({"linux": ["test1", "test2"]})]
    pendings = [
        gen_job_pending(builder='linux', requested_steps=['test1', 'test2'])
    ]
    if expect_mac_retry:
      # No need to run test2 again.
      expected_calls.append(_posted({"mac": ["test1"]}))
      pendings.append(gen_job_pending(builder='mac', requested_steps=['test1']))

    self.context.status.check_names(['try job rietveld'] * len(expected_calls))
    self.context.rietveld.check_calls(expected_calls)
    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      pendings=pendings,
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_failed=steps_failed,
          steps_passed=['test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0,
          completed=completed),
        })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationPreviousJobPartiallyGood1(self):
    self.timestamp = [1.] * 11
    # Only test1 will be run on mac since test2 had passed.
    self._previous_job_partially_good(
        [BuildbotBuildStep('test1', False), BuildbotBuildStep('test2', True)],
        ['test1'], True, True)

  def testVerificationPreviousJobPartiallyGood2(self):
    self.timestamp = [1.] * 11
    # Let's assume a testfilter was used and test1 wasn't run. Only test1 will
    # be run on mac.
    self._previous_job_partially_good(
        [BuildbotBuildStep('test2', True)], [], True, True)

  def testVerificationPreviousJobPartiallyGood3(self):
    self.timestamp = [1.] * 11
    # Test that we do not retry on mac until it completes.  This is because
    # CQ does not parse the test filter, so we do not know if the mac job
    # will run test1.
    self._previous_job_partially_good(
        [BuildbotBuildStep('test2', True)], [], False, False)

  def testVerificationPreviousJobsWereGood(self):
    self.timestamp = [1.] * 8
    # Reuse the previous jobs tests that passed. Do not send any try job.
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.try_runner.verify(self.pending)
    self.context.status.check_names([])
    self.context.rietveld.check_calls([])

    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1', 'test2'],
        'mac': ['test1', 'test2'],
      },
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_passed=['test1', 'test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0),
        key2: gen_job(
          build=32,
          builder='linux',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_passed=['test1', 'test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0),
        })
    self.assertEqual(expected, self._get_verif().as_dict())
    # People will love that!
    self.assertEqual(base.SUCCEEDED, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testRietveldTryJobsPendingWasLost(self):
    # Requested a pending try job but the request was lost.
    self.timestamp = [1.] * 7
    self.try_runner.builders_and_tests = {'linux': ['test1']}
    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'])
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1"]}),
        ])
    self.try_runner.update_status([self.pending])
    self.assertEqual(0, len(self.timestamp))

    # 3 minutes later
    later = 3. * 60
    self.timestamp = [later] * 3
    self.try_runner.update_status([self.pending])
    self.assertEqual(0, len(self.timestamp))
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1'],
      },
      pendings=[
        gen_job_pending(builder=u'linux', requested_steps=['test1']),
      ])
    verif = self._get_verif()
    self.assertEqual(expected, verif.as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())
    self.assertEqual({}, verif.tests_need_to_be_run())
    self.assertEqual({'linux': ['test1']}, verif.tests_waiting_for_result())

    # 1h later.
    later = 60. * 60
    self.timestamp = [later] * 5
    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1'],
      },
      pendings=[
        gen_job_pending(
            builder=u'linux', init_time=later, requested_steps=['test1']),
      ])
    verif = self._get_verif()
    self.assertEqual(expected, verif.as_dict())
    self.context.status.check_names(['try job rietveld'])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())
    self.assertEqual({}, verif.tests_need_to_be_run())
    self.assertEqual({'linux': ['test1']}, verif.tests_waiting_for_result())
    self.context.rietveld.check_calls([_posted({"linux": ["test1"]})])

  def testRietveldTryJobsPendingTookSomeTime(self):
    # Requested a pending try job but the request took some time to propagate.
    self.timestamp = [1.] * 7
    self.try_runner.builders_and_tests = {'linux': ['test1']}
    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'])
    self.context.rietveld.check_calls(
        [
          _posted({"linux": ["test1"]}),
        ])
    self.try_runner.update_status([self.pending])
    self.assertEqual(0, len(self.timestamp))
    # 3 minutes later
    later = 3. * 60
    self.timestamp = [later] * 3
    self.try_runner.update_status([self.pending])
    self.assertEqual(0, len(self.timestamp))
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1'],
      },
      pendings=[
        gen_job_pending(builder=u'linux', requested_steps=['test1']),
      ])
    verif = self._get_verif()
    self.assertEqual(expected, verif.as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())
    self.assertEqual({}, verif.tests_need_to_be_run())
    self.assertEqual({'linux': ['test1']}, verif.tests_waiting_for_result())

    # Queue it.
    self.try_runner.status.builders['linux'].pending_builds.data = [
      {
        "builderName":"linux",
        "builds":[],
        "reason":"%d-1: None" % self.pending.issue,
        "source": {
          "changes": [
            {
              "at": "Wed 05 Dec 2012 19:11:19",
              "files": [],
              "number": 268857,
              "project": "",
              "properties": [],
              "rev": "171358",
              "revision": "171358",
              "when": 1354763479,
              "who": self.pending.owner,
            },
          ],
          "hasPatch": False,
          "project": "chrome",
          "repository": "",
          "revision": "171358",
        },
        "submittedAt": 1354763479,
      },
    ]

    # 1h later, it must not have queued another job.
    later = 60. * 60
    self.timestamp = [later] * 3
    self.try_runner.update_status([self.pending])
    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1'],
      },
      pendings=[
        gen_job_pending(
            builder=u'linux', requested_steps=['test1']),
      ])
    verif = self._get_verif()
    self.assertEqual(expected, verif.as_dict())
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())
    self.assertEqual({}, verif.tests_need_to_be_run())
    self.assertEqual({'linux': ['test1']}, verif.tests_waiting_for_result())

  def testRietveldTryJobs_1(self):
    self.timestamp = [1.] * 2
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10', 'test11']
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    self.assertEqual({'builder1': ['test11']}, jobs.tests_need_to_be_run())
    self.assertEqual({'builder1': ['test11']}, jobs.tests_waiting_for_result())

  def testRietveldTryJobs_2(self):
    self.timestamp = [1.] * 3
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10', 'test11']
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.pendings.append(
        try_job_on_rietveld.RietveldTryJobPending(
            builder='builder1',
            revision=13,
            requested_steps=['test11'],
            clobber=False,
            tries=1))
    self.assertEqual({}, jobs.tests_need_to_be_run())
    self.assertEqual({'builder1': ['test11']}, jobs.tests_waiting_for_result())

  def testRietveldTryJobs_3(self):
    # Construct an instance that has both tests to trigger and tests that are
    # pending results.
    self.timestamp = [1.] * 5
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests = {
      'builder1': ['test10', 'test11'],
      'builder2': ['test20', 'test21'],
    }
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.try_jobs['key2'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder2',
        build=13,
        revision=14,
        requested_steps=[],
        started=int(time.time()),
        steps_passed=['test21'],
        steps_failed=[],
        clobber=False,
        completed=False,
        tries=1,
        parent_key=None)
    jobs.pendings.append(
        try_job_on_rietveld.RietveldTryJobPending(
            builder='builder2',
            revision=14,
            requested_steps=['test20'],
            clobber=False,
            tries=1))
    # test11 is still not queued to be run but build with test20 in it has still
    # not started yet.
    self.assertEqual({'builder1': ['test11']}, jobs.tests_need_to_be_run())
    self.assertEqual(
        {'builder1': ['test11'], 'builder2': ['test20']},
        jobs.tests_waiting_for_result())

  def testAddTriggeredBot(self):
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.update_triggered_builders([('tester1', 'builder1', ['test3'])])
    self.assertEqual({'builder1': ['test3']}, jobs.tests_need_to_be_run())
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())
    self.assertEqual({'tester1': 'builder1'}, jobs.triggered_builders)

  def testRietveldTriggeredTryJobs_1(self):
    """Test that we wait for trigger if builder is in progress."""
    self.timestamp = [1.] * 2
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10']
    jobs.update_triggered_builders([('tester1', 'builder1', ['test3'])])
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=False,
        tries=1,
        parent_key=None)
    self.assertEqual(jobs.parents_with_trigger_pending(),
                     set(['builder1']))
    self.assertEqual({}, jobs.tests_need_to_be_run())
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())

  def testRietveldTriggeredTryJobs_2(self):
    """Test that we wait for trigger if builder has recently completed."""
    self.timestamp = [1.] * 4
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10']
    jobs.update_triggered_builders([('tester1', 'builder1', ['test3'])])
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10', 'trigger'],
        started=int(time.time()),
        steps_passed=['test10', 'trigger'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    self.assertEqual(jobs.parents_with_trigger_pending(), set(['builder1']))
    self.assertEqual({}, jobs.tests_need_to_be_run())
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())

  def testRietveldTriggeredTryJobs_3(self):
    """Test that lost trigger jobs resend the parent."""
    self.timestamp = [1.] * 3
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10']
    jobs.update_triggered_builders([('tester1', 'builder1', ['test3'])])
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10', 'trigger'],
        started=int(time.time()),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.try_jobs['key1'].init_time = (
        time.time() - try_job_on_rietveld.PROPOGATION_DELAY_S - 1)

    self.assertEqual(set(), jobs.parents_with_trigger_pending())
    self.assertEqual({'builder1': ['test3']}, jobs.tests_need_to_be_run())
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())

  def testRietveldTriggeredTryJobs_4(self):
    """Test that failed trigger jobs resend the parent."""
    self.timestamp = [1.] * 4
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10']
    jobs.update_triggered_builders([('tester1', 'builder1', ['test3'])])
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10', 'trigger'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.try_jobs['key2'] = try_job_on_rietveld.RietveldTryJob(
        builder='tester1',
        build=12,
        revision=13,
        requested_steps=['test3'],
        started=int(time.time()),
        steps_passed=[],
        steps_failed=['test3'],
        clobber=False,
        completed=True,
        tries=1,
        parent_key='key1')

    self.assertEqual({'builder1': ['test3']}, jobs.tests_need_to_be_run())
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())

  def testRietveldTriggeredTryJobs_5(self):
    """Test failed trigger jobs do not send trigger if another is pending."""
    self.timestamp = [1.] * 8
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.builders_and_tests['builder1'] = ['test10']
    jobs.update_triggered_builders([('tester1', 'builder1', ['test3'])])
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10', 'trigger'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.try_jobs['key2'] = try_job_on_rietveld.RietveldTryJob(
        builder='builder1',
        build=13,
        revision=13,
        requested_steps=['test10'],
        started=int(time.time()),
        steps_passed=['test10', 'trigger'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.try_jobs['key3'] = try_job_on_rietveld.RietveldTryJob(
        builder='tester1',
        build=12,
        revision=13,
        requested_steps=['test3'],
        started=int(time.time()),
        steps_passed=[],
        steps_failed=['test3'],
        clobber=False,
        completed=True,
        tries=1,
        parent_key='key1')

    self.assertEqual(set(['builder1']), jobs.parents_with_trigger_pending())
    self.assertEqual({}, jobs.tests_need_to_be_run())
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())

  def testRietveldHung(self):
    self.try_runner.builders_and_tests = {
      'linux': ['test1'],
    }
    self.timestamp = [1.] * 9
    self.try_runner.verify(self.pending)
    self.context.status.check_names(['try job rietveld'])
    self.context.rietveld.check_calls([_posted({"linux": ["test1"]})])
    key1 = self._add_build(
        'linux', 32, 42,
        [],
        False)
    self.try_runner.update_status([self.pending])

    expected = gen_jobs(
      builders_and_tests={
        'linux': ['test1'],
      },
      try_jobs={
        key1: gen_job(
          builder=u'linux',
          build=32,
          requested_steps=['test1'],
          steps_passed=[],
          revision=42,
          completed=False),
      })

    self.assertEqual(0, len(self.timestamp))
    verif = self._get_verif()
    self.assertEqual(expected, verif.as_dict())

    self.assertEqual(set(), verif.parents_with_trigger_pending())
    self.timestamp = [1.]
    self.assertEqual({}, verif.tests_need_to_be_run())
    self.assertEqual({'linux': ['test1']}, verif.tests_waiting_for_result())

    self.context.status.check_names(['try job rietveld'])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

    # Fast forward in time to make it timeout.
    later = 40. * 24 * 60 * 60
    self.timestamp = [later] * 6
    self.try_runner.update_status([self.pending])

    self.assertEqual(0, len(self.timestamp))
    self.assertEqual({}, verif.tests_need_to_be_run())
    self.assertEqual({'linux': ['test1']}, verif.tests_waiting_for_result())

    self.context.status.check_names(['try job rietveld'])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

    expected_timed_out = gen_jobs(
      builders_and_tests={
        'linux': ['test1'],
      },
      irrelevant=[key1],
      pendings=[
        gen_job_pending(
            builder=u'linux', init_time=later, requested_steps=['test1']),
      ])
    self.assertEqual(expected_timed_out, verif.as_dict())
    self.context.rietveld.check_calls([_posted({"linux": ["test1"]})])


if __name__ == '__main__':
  logging.basicConfig(
      level=[logging.WARNING, logging.INFO, logging.DEBUG][
        min(sys.argv.count('-v'), 2)],
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  if '-v' in sys.argv:
    unittest.TestCase.maxDiff = None
  unittest.main()
