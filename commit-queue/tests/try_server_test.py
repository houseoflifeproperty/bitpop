#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/try_server.py."""

import json
import logging
import optparse
import os
import re
import StringIO
import sys
import time
import unittest
import urllib

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

# In tests/
import mocks  # pylint: disable=W0403

from testing_support import auto_stub

# In root
import buildbot_json
from verification import base
from verification import try_server

# pylint: disable=W0212
SUCCESS = buildbot_json.SUCCESS
WARNINGS = buildbot_json.WARNINGS
FAILURE = buildbot_json.FAILURE
SKIPPED = buildbot_json.SKIPPED
EXCEPTION = buildbot_json.EXCEPTION


class FakeTryServer(auto_stub.SimpleMock):
  """Stateful try server mock.

  Includes calls to send try jobs TryChange() and visible results from HTTP
  requests.
  """
  def __init__(self, unit_test):
    super(FakeTryServer, self).__init__(unit_test)

    # Try server immutable properties.
    self.steps = ['update', 'compile', 'test1', 'test2']
    self.server_url = 'http://foo/bar'

    # State of the try server.
    self._builds = { 'linux': [], 'mac': [] }
    self.pending_builds = {
      'linux': [],
      'mac': []
    }
    # Default mocks.
    self.unit_test.mock(urllib, 'urlopen', self._mockurlopen)
    self.unit_test.mock(try_server.trychange, 'TryChange', self.TryChangeMock)

  def TryChangeMock(self, cmd, _change, swallow_exception):
    """Mocks trychange.py."""
    self.assertEquals(swallow_exception, True)
    parser = optparse.OptionParser()
    parser.add_option('--bot', action='append')
    parser.add_option('--clobber', action='store_true', default=False)
    parser.add_option('--email')
    parser.add_option('--issue', type='int')
    parser.add_option('--name')
    parser.add_option('--no_search', action='store_true')
    parser.add_option('--patchset', type='int')
    parser.add_option('--revision')
    parser.add_option('--rietveld_url')
    parser.add_option('--user')
    options, args = parser.parse_args(cmd)
    self.assertEquals(options.email, 'user1@example.com')
    self.assertEquals(options.issue, 42)
    self.assertEquals(options.no_search, True)
    self.assertEquals(options.patchset, 23)
    self.assertEquals(
        options.rietveld_url,
        '%s/download/issue42_23.diff' % self.unit_test.context.rietveld.url)
    self.assertEquals(options.user, 'user1')
    self.assertEquals(args, ['extra_flags'])
    bot = ', '.join(options.bot)
    call = 'trychange b={%s} c=%s r=%s' % (
        bot, options.clobber, options.revision)
    if options.name != '42-23':
      call += ' n=%s' % options.name
    self.calls.append(call)
    logging.debug(self.calls[-1])

  def _mockurlopen_internal(self, sub_url):
    """Returns data to be encoded before returning."""
    # sub_url is str on python <= 2.6 and unicode for >= 2.7
    self.unit_test.assertTrue(isinstance(sub_url, basestring))
    expected_url = self.server_url + '/json/'
    self.unit_test.assertTrue(sub_url.startswith(expected_url))
    self.calls.append(sub_url[len(expected_url):])
    baseurl = '^%s/json/' % re.escape(self.server_url)
    match = re.match(baseurl + r'builders/(\w+)/builds/\?(.+)$', sub_url)
    if match:
      data = {}
      for query in match.group(2).split('&'):
        m = re.match(r'select=(\w+)', query)
        self.unit_test.assertTrue(m, (match.group(2), query))
        build = int(m.group(1))
        data[str(build)] = self._builds[match.group(1)][build]
      return data

    match = re.match(baseurl + r'builders/(\w+)/builds/_all$', sub_url)
    if match:
      # Data is not stored exactly as the try server serves it.
      data = {}
      for i, build in enumerate(self._builds[match.group(1)]):
        data[str(i)] = build
      return data

    match = re.match(baseurl + r'builders/\?(.+)$', sub_url)
    if match:
      data = {}
      for query in match.group(1).split('&'):
        m = re.match(r'select=(\w+)', query)
        self.unit_test.assertTrue(m, (match.group(1), query))
        builder = m.group(1)
        data[builder] = {
          'cachedBuilds': range(len(self._builds[builder])),
          'pendingBuilds': len(self.pending_builds.get(builder, [])),
        }
      return data

    match = re.match(baseurl + r'builders/(\w+)/pendingBuilds$', sub_url)
    if match:
      return self.pending_builds[match.group(1)]

  def _mockurlopen(self, sub_url):
    """Mocks urllib.urlopen() and JSON encode + StringIO buffers."""
    sub_url = re.match(r'^(.+)[\&\?]filter=1$', sub_url).group(1)
    data = self._mockurlopen_internal(sub_url)
    self.unit_test.assertNotEquals(None, data, sub_url)
    #logging.debug('_mockurlopen(%s) -> %s' % (sub_url, data))
    return StringIO.StringIO(json.dumps(data))

  def add_build(self, builder, revision, reason, step_results):
    """Add a build to a builder."""
    self.assertEquals(len(self.steps), len(step_results))
    assert isinstance(revision, (str, int))
    data = {
      'reason': reason or self.unit_test.pending.pending_name(),
      'sourceStamp': {
        'revision': 'sol@%s' % revision,
        'hasPatch': True,
      },
      'steps': [],
      'blame': ['user1@example.com'],
      'number': 0,
      'slave': 'foo',
    }
    result = max(step_results)
    if result in (SUCCESS, WARNINGS) and step_results[-1] is None:
      result = None
    for i, step in enumerate(self.steps):
      data['steps'].append({
        'name': step,
        'results': [step_results[i]],
      })
    data['results'] = [result]
    self._builds[builder].append(data)

  def set_build_result(self, builder, result):
    """Override the build result for every steps to |result|."""
    for step in self._builds[builder][-1]['steps']:
      step['results'] = [result]
    self._builds[builder][-1]['results'] = [result]


class TryServerSvnTest(mocks.TestCase):
  def setUp(self):
    super(TryServerSvnTest, self).setUp()
    self.email = 'user1@example.com'
    self.user = 'user1'
    self.timestamp = [1.]
    # Mocks http://chromium-status.appspot.com/lkgr
    self.lkgr = 123
    self.try_server = FakeTryServer(self)
    self.mock(time, 'time', lambda: self.timestamp[-1])

    try_server.TryRunnerSvn.update_latency = 0
    self.builders_and_tests = {
      'linux': ['test1', 'test2'],
      'mac': ['test1', 'test2'],
    }
    self.try_runner = try_server.TryRunnerSvn(
        self.context,
        self.try_server.server_url,
        self.email,
        self.builders_and_tests,
        ['ignored_step'],
        'sol',
        ['extra_flags',],
        lambda: self.lkgr,
        )
    self.pending.revision = 123

  def tearDown(self):
    self.try_server.check_calls([])
    super(TryServerSvnTest, self).tearDown()

  def get_verif(self):
    return self.pending.verifications[self.try_runner.name]

  def assertPending(
      self, state, nb_jobs, error_message,
      linux_build=1,
      mac_build=1,
      linux_state=None,
      mac_state=None,
      linux_clobber=False,
      mac_clobber=False,
      linux_rev=123,
      mac_rev=123,
      linux_sent=1,
      mac_sent=1,
      linux_name='42-23',
      mac_name='42-23'):
    if linux_state is None:
      linux_state = state
    if mac_state is None:
      mac_state = state
    self.assertEquals([self.try_runner.name], self.pending.verifications.keys())
    self.assertEquals(error_message, self.get_verif().error_message)
    self.assertEquals(nb_jobs, len(self.get_verif().try_jobs))
    self.assertEquals(
        len(self.builders_and_tests), len(self.get_verif().try_jobs))
    self.assertEquals(linux_name, self.get_verif().try_jobs[0].name)
    self.assertEquals('linux', self.get_verif().try_jobs[0].builder)
    self.assertEquals(linux_rev, self.get_verif().try_jobs[0].revision)
    self.assertEquals(linux_sent, self.get_verif().try_jobs[0].sent)
    self.assertEquals(linux_clobber, self.get_verif().try_jobs[0].clobber)
    self.assertEquals(linux_build, self.get_verif().try_jobs[0].build)
    self.assertEquals(linux_state, self.get_verif().try_jobs[0].get_state())
    if len(self.builders_and_tests) > 1:
      self.assertEquals(mac_name, self.get_verif().try_jobs[1].name)
      self.assertEquals('mac', self.get_verif().try_jobs[1].builder)
      self.assertEquals(mac_rev, self.get_verif().try_jobs[1].revision)
      self.assertEquals(mac_sent, self.get_verif().try_jobs[1].sent)
      self.assertEquals(mac_clobber, self.get_verif().try_jobs[1].clobber)
      self.assertEquals(mac_build, self.get_verif().try_jobs[1].build)
      self.assertEquals(mac_state, self.get_verif().try_jobs[1].get_state())
    self.assertEquals(state, self.get_verif().get_state())

  def testVoid(self):
    self.assertEquals(self.pending.verifications.keys(), [])

  def testVerificationVoid(self):
    self.try_runner.verify(self.pending)
    self.assertPending(base.PROCESSING, 2, None, linux_build=None,
        mac_build=None)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    self.context.status.check_names(['try server'] * 2)

  def testVoidUpdate(self):
    self.try_runner.update_status([])

  def test_steps_quality(self):
    self.assertEquals(None, try_server.steps_quality([]))
    self.assertEquals(True, try_server.steps_quality([True, None]))
    self.assertEquals(False, try_server.steps_quality([True, None, False]))

  def testStepQualityNone(self):
    self.try_runner.status.builders['linux'].builds.cache()
    self.assertEquals(
        (None, 0),
        self.try_runner.step_db.revision_quality_builder_steps('linux', 123))
    self.try_server.check_calls(['builders/linux/builds/_all'])

  def testStepQualityGood(self):
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, None, None, None])
    self.try_runner.status.builders['linux'].builds.cache()
    self.try_server.check_calls(['builders/linux/builds/_all'])
    self.assertEquals(
        ([True, None, None, None], 1),
        self.try_runner.step_db.revision_quality_builder_steps('linux', 123))
    self.try_server.set_build_result('linux', SUCCESS)
    self.try_runner.status.builders['linux'].builds.refresh()
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps('linux', 123))
    self.try_server.check_calls(['builders/linux/builds/_all'])

  def testStepQualityBad(self):
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, FAILURE, SUCCESS])
    self.try_runner.status.builders['linux'].builds.cache()
    # Also test that FakeTryServer.add_build() is implemented correctly.
    self.assertEquals(
        ([True, True, False, True], 1),
        self.try_runner.step_db.revision_quality_builder_steps('linux', 123))
    self.try_server.check_calls(['builders/linux/builds/_all'])

  def testStepQualityBadIncomplete(self):
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, FAILURE, None])
    self.try_runner.status.builders['linux'].builds.cache()
    # Also test that FakeTryServer.add_build() is implemented correctly.
    self.assertEquals(
        ([True, True, False, None], 1),
        self.try_runner.step_db.revision_quality_builder_steps('linux', 123))
    self.try_server.check_calls(['builders/linux/builds/_all'])

  def testStepQualityGoodAndBad(self):
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_server.add_build('linux', 123, None, [FAILURE, None, None, None])
    self.try_runner.status.builders['linux'].builds.cache()
    self.try_server.check_calls(['builders/linux/builds/_all'])
    self.assertEquals(
        ([True] * 4, 2),
        self.try_runner.step_db.revision_quality_builder_steps('linux', 123))

  def testQualityAutomatic(self):
    self.try_runner.verify(self.pending)
    self.assertEquals(
        (None, 0),
        self.try_runner.step_db.revision_quality_builder_steps(
          'linux', 123))
    self.try_server.add_build(
        'linux', 123, 'georges tried stuff',
        [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_runner.update_status([self.pending])
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'linux', 123))
    self.try_server.check_calls(
        [ 'trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123',
          'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])
    self.context.status.check_names(['try server'] * 2)

  def testQualityManual(self):
    self.try_server.add_build(
        'linux', 123, 'georges tried stuff',
        [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_runner.status.builders['linux'].builds.cache()
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'linux', 123))
    self.try_server.check_calls(['builders/linux/builds/_all'])

  def _simple(self, status_linux, status_mac=None, error_msg=None):
    """status_linux affects test1, status_mac affects test2."""
    def is_failure(status):
      return status in (FAILURE, EXCEPTION)

    self.assertEquals(
        bool(is_failure(status_linux) or is_failure(status_mac)),
        bool(error_msg))
    if status_mac is None:
      status_mac = status_linux
    self.lkgr = 12
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_server.add_build(
        'mac', 123, None, [SUCCESS, SUCCESS, SUCCESS, SUCCESS])

    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, status_linux, SUCCESS])
    self.try_server.add_build(
        'mac', 123, None, [SUCCESS, SUCCESS, SUCCESS, status_mac])
    self.try_runner.update_status([self.pending])

    if is_failure(status_linux):
      self.assertEquals(123, self.try_runner.get_lkgr('linux'))
      self.assertEquals(
          123, self.try_runner.step_db.last_good_revision_builder('linux'))
    else:
      self.assertEquals(123, self.try_runner.get_lkgr('linux'))
      self.assertEquals(
          123, self.try_runner.step_db.last_good_revision_builder('linux'))
    if is_failure(status_mac):
      self.assertEquals(123, self.try_runner.get_lkgr('mac'))
      self.assertEquals(
          123, self.try_runner.step_db.last_good_revision_builder('mac'))
    else:
      self.assertEquals(123, self.try_runner.get_lkgr('mac'))
      self.assertEquals(
          123, self.try_runner.step_db.last_good_revision_builder('mac'))

    if error_msg:
      # Can't test failure without testing automatic retry mechanism.
      expected = (
          [ 'builders/?select=linux&select=mac',
            'builders/linux/builds/_all', 'builders/mac/builds/_all'])

      if is_failure(status_linux):
        expected.append(
            'trychange b={linux:test1} c=False r=sol@123 n=42-23 (retry)')
        linux_build = None
        linux_state = base.PROCESSING
        linux_name = '42-23 (retry)'
      else:
        linux_build = 1
        linux_state = base.SUCCEEDED
        linux_name = '42-23'

      if is_failure(status_mac):
        expected.append(
            'trychange b={mac:test2} c=False r=sol@123 n=42-23 (retry)')
        mac_build = None
        mac_state = base.PROCESSING
        mac_name = '42-23 (retry)'
      else:
        mac_build = 1
        mac_state = base.SUCCEEDED
        mac_name = '42-23'

      self.assertPending(
          base.PROCESSING, 2, None, linux_build=linux_build,
          mac_build=mac_build, linux_state=linux_state, mac_state=mac_state,
          linux_name=linux_name, mac_name=mac_name)
      self.try_server.check_calls(expected)

      if is_failure(status_linux):
        self.try_server.add_build(
            'linux', 123, linux_name, [SUCCESS, SUCCESS, status_linux, SUCCESS])
      if is_failure(status_mac):
        self.try_server.add_build(
            'mac', 123, mac_name, [SUCCESS, SUCCESS, SUCCESS, status_mac])

      self.try_runner.update_status([self.pending])
      if is_failure(status_linux):
        linux_state = base.FAILED
        linux_build = 2
      else:
        linux_build = 1
      if is_failure(status_mac):
        mac_state = base.FAILED
        mac_build = 2
      else:
        mac_build = 1
      self.assertPending(
          base.FAILED, 2, error_msg,
          linux_build=linux_build, mac_build=mac_build,
          linux_state=linux_state, mac_state=mac_state,
          linux_name=linux_name, mac_name=mac_name)

      if is_failure(status_linux) and is_failure(status_mac):
        self.try_server.check_calls(
            [ 'builders/?select=linux&select=mac',
              'builders/linux/builds/_all', 'builders/mac/builds/_all'])
        self.context.checkout.check_calls(
            [ 'prepare(123)',
              'apply_patch(%r)' % self.context.rietveld.patchsets[-2],
              'prepare(123)',
              'apply_patch(%r)' % self.context.rietveld.patchsets[-1]])
      elif is_failure(status_linux):
        self.try_server.check_calls(
            ['builders/?select=linux', 'builders/linux/builds/_all'])
        self.context.checkout.check_calls(
            [ 'prepare(123)',
              'apply_patch(%r)' % self.context.rietveld.patchsets[-1]])
      else:
        self.try_server.check_calls(
            ['builders/?select=mac', 'builders/mac/builds/_all'])
        self.context.checkout.check_calls(
            [ 'prepare(123)',
              'apply_patch(%r)' % self.context.rietveld.patchsets[-1]])
    else:
      self.assertPending(base.SUCCEEDED, 2, None)
      self.try_server.check_calls(
          [ 'builders/?select=linux&select=mac',
            'builders/linux/builds/_all', 'builders/mac/builds/_all'])
    count = 6 + 3 * (
        int(is_failure(status_linux)) + int(is_failure(status_mac)))
    self.context.status.check_names(['try server'] * count)

  def testImmediateSuccess(self):
    self._simple(SUCCESS)

  def testImmediateWarnings(self):
    self._simple(WARNINGS)

  def testImmediateSkipped(self):
    self._simple(SKIPPED)

  def second_fail_msg(
      self, clname, step2, step1, builder, number, is_clobber=False):
    extra = ''
    if is_clobber:
      extra = ' (clobber build)'
    return (
        u'Try job failure for %s on %s for step "%s"%s.\n'
        u'It\'s a second try, previously, step "%s" failed.\n'
        u'%s/buildstatus?builder=%s&number=%s\n') % (
            clname, builder, step2, extra, step1, self.try_server.server_url,
            builder, number)
  def testImmediateFailureLinux(self):
    self._simple(
        FAILURE, SUCCESS,
        self.second_fail_msg('42-23 (retry)', 'test1', 'test1', 'linux', 2))

  def testImmediateFailureMac(self):
    self._simple(
        SUCCESS, FAILURE,
        self.second_fail_msg('42-23 (retry)', 'test2', 'test2', 'mac', 2))

  def testImmediateDoubleFailure(self):
    self._simple(
        FAILURE, FAILURE,
        self.second_fail_msg('42-23 (retry)', 'test2', 'test2', 'mac', 2))

  def testImmediateException(self):
    self._simple(
        SUCCESS, EXCEPTION,
        self.second_fail_msg('42-23 (retry)', 'test2', 'test2', 'mac', 2))

  def testSuccess(self):
    self.lkgr = 2
    # Normal workflow with incremental success.
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])

    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.PROCESSING, 2, None, linux_build=None, mac_build=None)
    self.try_server.check_calls(
        ['builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])

    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, None, None, None])
    self.try_runner.update_status([self.pending])
    self.assertPending(base.PROCESSING, 2, None, linux_build=0, mac_build=None)
    self.try_server.check_calls(
        ['builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])

    self.try_server.add_build(
        'mac', 123, None, [SUCCESS, None, None, None])
    self.try_runner.update_status([self.pending])
    self.assertPending(base.PROCESSING, 2, None, linux_build=0, mac_build=0)
    self.try_server.check_calls(
        ['builders/?select=mac',
          'builders/mac/builds/_all', 'builders/linux/builds/?select=0'])

    # This one will be cached since it's now immutable.
    self.try_server.set_build_result('mac', SUCCESS)
    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.PROCESSING, 2, None, linux_build=0, mac_build=0,
        mac_state=base.SUCCEEDED)
    self.try_server.check_calls(
        ['builders/linux/builds/?select=0', 'builders/mac/builds/?select=0'])

    self.try_server.set_build_result('linux', SUCCESS)
    self.try_runner.update_status([self.pending])
    self.assertPending(base.SUCCEEDED, 2, None, linux_build=0, mac_build=0)
    self.assertEquals(
        123, self.try_runner.step_db.last_good_revision_builder('linux'))
    self.assertEquals(
        123, self.try_runner.step_db.last_good_revision_builder('mac'))
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'linux', 123))
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'mac', 123))
    self.try_server.check_calls(['builders/linux/builds/?select=0'])
    self.context.status.check_names(['try server'] * 6)

  def testIgnorePreviousJobs(self):
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])

    self.try_runner.update_status([self.pending])
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])

    self.try_server.add_build('linux', 12, None, [None, None, None, None])
    self.try_server.add_build('mac', 12, None, [None, None, None, None])
    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.PROCESSING, 2, None, linux_build=None,
        mac_build=None)
    self.try_server.check_calls(
        ['builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])

    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_server.add_build(
        'mac', 123, None, [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_runner.update_status([self.pending])
    self.assertPending(base.SUCCEEDED, 2, None)
    self.assertEquals(
        123, self.try_runner.step_db.last_good_revision_builder('linux'))
    self.assertEquals(
        123, self.try_runner.step_db.last_good_revision_builder('mac'))
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'linux', 123))
    self.assertEquals(
        ([True] * 4, 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'mac', 123))
    self.try_server.check_calls(
        ['builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])
    self.context.status.check_names(['try server'] * 6)

  def testNames(self):
    job = try_server.TryJob(
        builder='builder', revision=123, tests=['test1'], clobber=False)
    self.assertEquals(None, job.name)

  def testLostJob(self):
    # Test that a job is automatically retried if it was never started up. It
    # does happen.
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])

    # Keep a copy of the try jobs to compare later.
    self.try_runner.update_status([self.pending])
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])
    self.assertPending(
        base.PROCESSING, 2, None, mac_sent=self.timestamp[-1],
        linux_build=None, mac_build=None)

    # lost_try_job_delay + 2 seconds later.
    # linux is pending, mac is lost.
    self.try_server.pending_builds['linux'] = [
      {
        'reason': '42-23',
      }
    ]
    self.timestamp.append(self.try_runner.lost_try_job_delay + 2)
    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.PROCESSING, 2, None, mac_sent=self.timestamp[-1],
        linux_build=None, mac_build=None,
        mac_name='42-23 (previous was lost)')
    self.try_server.check_calls(
        # Look if there is pending build on each builder.
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all',
          'builders/linux/pendingBuilds',
          # Retry only mac.
          'trychange b={mac:test1,test2} c=False r=sol@123 n=42-23 (previous '
          'was lost)'])

    # linux job was completed.
    self.try_server.pending_builds['linux'] = []
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.PROCESSING, 2, None, mac_sent=self.timestamp[1],
        linux_build=0, mac_build=None,
        linux_state=base.SUCCEEDED,
        mac_name='42-23 (previous was lost)')
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])

    # 2 * (lost_try_job_delay + 2) seconds later, mac job started and completed.
    self.timestamp.append(2 * (self.try_runner.lost_try_job_delay + 2))
    self.try_server.add_build(
        'mac', 123, '42-23 (previous was lost)',
        [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.SUCCEEDED, 2, None, mac_sent=self.timestamp[1],
        linux_build=0, mac_build=0,
        mac_name='42-23 (previous was lost)')
    self.try_server.check_calls(
        ['builders/?select=mac', 'builders/mac/builds/_all'])

    self.try_runner.update_status([self.pending])
    self.context.checkout.check_calls(
        [ 'prepare(123)',
          'apply_patch(%r)' % self.context.rietveld.patchsets[-1]])
    self.context.status.check_names(['try server'] * 7)

  def testFailedStepRetryLkgr(self):
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, FAILURE, SUCCESS])

    self.lkgr = 122
    self.try_runner.update_status([self.pending])
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all',
          # Only the failed test is retried, on lkgr revision.
          'trychange b={linux:test1} c=False r=sol@122 n=42-23 (retry)'])
    self.assertEquals(['test1'], self.get_verif().try_jobs[0].failed_steps)
    self.context.checkout.check_calls(
        [ 'prepare(122)',
          'apply_patch(%r)' % self.context.rietveld.patchsets[-1]])
    self.context.status.check_names(['try server'] * 5)

  def testFailedUpdate(self):
    # It must not retry a failed update.
    # Add succeededing builds, this sets quality to True, which disable retry
    # mechanism.
    self.try_server.add_build(
        'linux', 123, 'georges tried stuff',
        [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.try_server.add_build(
        'mac', 123, 'georges tried stuff', [SUCCESS, SUCCESS, SUCCESS, SUCCESS])
    self.lkgr = 123

    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    self.try_server.add_build(
        'linux', 123, None, [FAILURE, None, None, None])
    self.try_runner.update_status([self.pending])
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])
    self.assertEquals('linux', self.get_verif().try_jobs[0].builder)
    self.assertEquals(['update'], self.get_verif().try_jobs[0].failed_steps)
    self.assertPending(
        base.FAILED, 2,
        (u'Try job failure for 42-23 on linux for step '
        u'"update".\n%s/buildstatus?builder=linux&number=1\n\n'
        u'Step "update" is always a major failure.\n'
        u'Look at the try server FAQ for more details.') %
            self.try_server.server_url,
        mac_build=None,
        mac_state=base.PROCESSING)
    self.context.status.check_names(['try server'] * 4)

  def testFailedCompileRetryClobber(self):
    # It must retry once a non-clobber compile.
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, FAILURE, None, None])
    self.lkgr = 122
    self.try_runner.update_status([self.pending])
    self.context.checkout.check_calls(
        [ 'prepare(122)',
          'apply_patch(%r)' % self.context.rietveld.patchsets[-1]])
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all',
          # Retries at lkgr.
          'trychange b={linux:test1,test2} c=True r=sol@122 n=42-23 (retry)'])
    self.assertEquals(['compile'], self.get_verif().try_jobs[0].failed_steps)
    self.assertPending(
        base.PROCESSING, 2, None, linux_rev=122,
        linux_clobber=True, linux_build=None, mac_build=None,
        linux_name='42-23 (retry)')

    self.try_server.add_build(
        'linux', 122, '42-23 (retry)', [SUCCESS, FAILURE, None, None])
    self.try_runner.update_status([self.pending])
    self.try_server.check_calls(
        [ 'builders/?select=linux&select=mac',
          'builders/linux/builds/_all', 'builders/mac/builds/_all'])
    self.assertEquals(['compile'], self.get_verif().try_jobs[0].failed_steps)
    self.assertPending(
        base.FAILED, 2,
        self.second_fail_msg('42-23 (retry)', 'compile', 'compile', 'linux', 1,
            True),
        linux_rev=122,
        linux_clobber=True,
        mac_build=None,
        mac_state=base.PROCESSING,
        linux_name='42-23 (retry)')
    self.context.status.check_names(['try server'] * 7)

  def testTooManyRetries(self):
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    job = self.pending.verifications[self.try_runner.name].try_jobs[0]
    self.try_runner._send_jobs(
        self.pending, [job], False, {job.builder:job.tests}, 'foo')
    self.try_server.check_calls(
        [ 'trychange b={linux:test1,test2} c=False r=sol@123 n=foo'])
    job = self.pending.verifications[self.try_runner.name].try_jobs[0]
    self.try_runner._send_jobs(
        self.pending, [job], False, {job.builder:job.tests}, 'foo')
    self.try_server.check_calls(
        [ 'trychange b={linux:test1,test2} c=False r=sol@123 n=foo'])
    job = self.pending.verifications[self.try_runner.name].try_jobs[0]
    self.try_runner._send_jobs(
        self.pending, [job], False, {job.builder:job.tests}, 'foo')
    self.try_server.check_calls(
        [ 'trychange b={linux:test1,test2} c=False r=sol@123 n=foo'])
    job = self.pending.verifications[self.try_runner.name].try_jobs[0]
    try:
      self.try_runner._send_jobs(
          self.pending, [job], False, {job.builder:job.tests}, 'foo')
      self.fail()
    except base.DiscardPending:
      pass
    self.context.status.check_names(['try server'] * 5)

  def testNoTry(self):
    self.pending.description += '\nNOTRY=true'
    self.try_runner.verify(self.pending)
    self.assertEquals(
        base.SUCCEEDED,
        self.pending.verifications[self.try_runner.name].get_state())

  def testNoTryWrong(self):
    self.pending.description += '\nNOTRY=true2'
    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2, mac:test1,test2} c=False r=sol@123'])
    self.context.status.check_names(['try server'] * 2)
    self.assertEquals(
        base.PROCESSING,
        self.pending.verifications[self.try_runner.name].get_state())

  def testSuccessIgnoredFailure(self):
    # Simplify testing code by removing mac.
    del self.try_runner.builders_and_tests['mac']
    # Add fake failing ignored step.
    self.try_server.steps = [
        'update', 'compile', 'ignored_step', 'test1', 'test2']

    self.try_runner.verify(self.pending)
    self.try_server.check_calls(
        ['trychange b={linux:test1,test2} c=False r=sol@123'])

    self.try_runner.update_status([self.pending])
    self.assertPending(
        base.PROCESSING, 1, None, linux_build=None, mac_build=None)
    self.try_server.check_calls(
        ['builders/?select=linux', 'builders/linux/builds/_all'])

    self.try_server.add_build(
        'linux', 123, None, [SUCCESS, SUCCESS, FAILURE, SUCCESS, SUCCESS])
    self.try_runner.update_status([self.pending])
    self.assertPending(base.SUCCEEDED, 1, None, linux_build=0, mac_build=None)
    self.try_server.check_calls(
        ['builders/?select=linux', 'builders/linux/builds/_all'])

    self.try_server.set_build_result('linux', SUCCESS)
    self.try_runner.update_status([self.pending])
    self.assertPending(base.SUCCEEDED, 1, None, linux_build=0, mac_build=0)
    # TODO(maruel): Fix, since StepDb doesn't know about ignored steps.
    self.assertEquals(
        None, self.try_runner.step_db.last_good_revision_builder('linux'))
    self.assertEquals(
        ([True, True, False, True, True], 1),
        self.try_runner.step_db.revision_quality_builder_steps(
          'linux', 123))
    self.context.status.check_names(['try server'] * 3)


if __name__ == '__main__':
  logging.basicConfig(
      level=[logging.WARNING, logging.INFO, logging.DEBUG][
        min(sys.argv.count('-v'), 2)],
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
