#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test cases for results_dashboard."""

import datetime
import json
import os
import shutil
import tempfile
import time
import unittest
import urllib
import urllib2

import test_env  # pylint: disable=W0403,W0611

from slave import results_dashboard
from slave import slave_utils
from testing_support.super_mox import mox


class FakeDateTime(object):
  # pylint: disable=R0201
  def utctimetuple(self):
    return time.struct_time((2013, 8, 1, 0, 0, 0, 3, 217, 0))


class ResultsDashboardFormatTest(unittest.TestCase):
  """Tests related to functions which convert data format."""

  def setUp(self):
    super(ResultsDashboardFormatTest, self).setUp()
    self.mox = mox.Mox()
    self.maxDiff = None

  def tearDown(self):
    self.mox.UnsetStubs()

  def test_MakeListOfPoints_MinimalCase(self):
    """A very simple test of a call to MakeListOfPoints."""

    # The master name is gotten when making the list of points,
    # so it must be stubbed out here.
    self.mox.StubOutWithMock(slave_utils, 'GetActiveMaster')
    slave_utils.GetActiveMaster().AndReturn('MyMaster')
    self.mox.ReplayAll()

    actual_points = results_dashboard.MakeListOfPoints(
        {
            'bar': {
                'traces': {'baz': ["100.0", "5.0"]},
                'rev': '12345',
            }
        },
        'my-bot', 'foo_test', 'my.master', 'Builder', 10, {})
    expected_points = [
        {
            'master': 'MyMaster',
            'bot': 'my-bot',
            'test': 'foo_test/bar/baz',
            'revision': 12345,
            'value': '100.0',
            'error': '5.0',
            'masterid': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 10,
            'supplemental_columns': {},
        }
    ]
    self.assertEqual(expected_points, actual_points)

  def test_MakeListOfPoints_GeneralCase(self):
    """A test of making a list of points, including all optional data."""
    # The master name is gotten when making the list of points,
    # so it must be stubbed out here.
    self.mox.StubOutWithMock(slave_utils, 'GetActiveMaster')
    slave_utils.GetActiveMaster().AndReturn('MyMaster')
    self.mox.ReplayAll()

    actual_points = results_dashboard.MakeListOfPoints(
        {
            'bar': {
                'traces': {
                    'bar': ['100.0', '5.0'],
                    'bar_ref': ['98.5', '5.0'],
                },
                'rev': '12345',
                'git_revision': '46790669f8a2ecd7249ab92418260316b1c60dbf',
                'webkit_rev': '6789',
                'v8_rev': 'undefined',
                'units': 'KB',
            },
            'x': {
                'traces': {
                    'y': [10.0, 0],
                },
                'important': ['y'],
                'rev': '23456',
                'git_revision': '46790669f8a2ecd7249ab92418260316b1c60dbf',
                'v8_rev': '2345',
                'units': 'count',
            },
        },
        'my-bot', 'foo_test', 'my.master', 'Builder', 10,
        {
            'r_bar': '89abcdef',
            'a_stdio_uri': 'http://mylogs.com/Builder/10',
            # The supplemental columns here are included in all points.
        })
    expected_points = [
        {
            'master': 'MyMaster',
            'bot': 'my-bot',
            'test': 'foo_test/bar', # Note that trace name is omitted.
            'revision': 12345,
            'value': '100.0',
            'error': '5.0',
            'units': 'KB',
            'masterid': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 10,
            'supplemental_columns': {
                'r_webkit_rev': '6789',
                'r_bar': '89abcdef',
                'r_chromium': '46790669f8a2ecd7249ab92418260316b1c60dbf',
                'a_stdio_uri': 'http://mylogs.com/Builder/10',
                # Note that v8 rev is not included since it was 'undefined'.
            },
        },
        {
            'master': 'MyMaster',
            'bot': 'my-bot',
            'test': 'foo_test/bar/ref',  # Note the change in trace name.
            'revision': 12345,
            'value': '98.5',
            'error': '5.0',
            'units': 'KB',
            'masterid': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 10,
            'supplemental_columns': {
                'r_webkit_rev': '6789',
                'r_bar': '89abcdef',
                'r_chromium': '46790669f8a2ecd7249ab92418260316b1c60dbf',
                'a_stdio_uri': 'http://mylogs.com/Builder/10',
            },
        },
        {
            'master': 'MyMaster',
            'bot': 'my-bot',
            'test': 'foo_test/x/y',
            'revision': 23456,
            'value': 10.0,
            'error': 0,
            'units': 'count',
            'important': True,
            'masterid': 'my.master',
            'buildername': 'Builder',
            'buildnumber': 10,
            'supplemental_columns': {
                'r_v8_rev': '2345',
                'r_bar': '89abcdef',
                'r_chromium': '46790669f8a2ecd7249ab92418260316b1c60dbf',
                'a_stdio_uri': 'http://mylogs.com/Builder/10',
            },
        },
    ]
    self.assertEqual(expected_points, actual_points)

  def test_MakeListOfPoints_TimestampUsedWhenRevisionIsNaN(self):
    """Tests sending data with a git hash as "revision"."""
    self.mox.StubOutWithMock(datetime, 'datetime')
    datetime.datetime.utcnow().AndReturn(FakeDateTime())
    self.mox.StubOutWithMock(slave_utils, 'GetActiveMaster')
    slave_utils.GetActiveMaster().AndReturn('ChromiumPerf')
    self.mox.ReplayAll()

    actual_points = results_dashboard.MakeListOfPoints(
        {
            'bar': {
                'traces': {'baz': ["100.0", "5.0"]},
                'rev': '2eca27b067e3e57c70e40b8b95d0030c5d7c1a7f',
            }
        },
        'my-bot', 'foo_test', 'chromium.perf', 'Builder', 10, {})
    expected_points = [
        {
            'master': 'ChromiumPerf',
            'bot': 'my-bot',
            'test': 'foo_test/bar/baz',
            # Corresponding timestamp for the fake datetime is used.
            'revision': 1375315200,
            'value': '100.0',
            'error': '5.0',
            'masterid': 'chromium.perf',
            'buildername': 'Builder',
            'buildnumber': 10,
            'supplemental_columns': {
                'r_chromium': '2eca27b067e3e57c70e40b8b95d0030c5d7c1a7f',
            },
        }
    ]
    self.assertEqual(expected_points, actual_points)

  def test_BlinkUsesTimestamp(self):
    """Tests that timestamp is used for "revision" for ChromiumWebkit master."""
    self.mox.StubOutWithMock(datetime, 'datetime')
    datetime.datetime.utcnow().AndReturn(FakeDateTime())
    self.mox.StubOutWithMock(slave_utils, 'GetActiveMaster')
    slave_utils.GetActiveMaster().AndReturn('ChromiumWebkit')
    self.mox.ReplayAll()

    actual_points = results_dashboard.MakeListOfPoints(
        {
            'bar': {
                'traces': {'baz': ["100.0", "5.0"]},
                'rev': '123456',
                'webkit_rev': '23456',
            }
        },
        'my-bot', 'foo_test', 'chromium.webkit', 'Builder', 10, {})
    expected_points = [
        {
            'master': 'ChromiumWebkit',
            'bot': 'my-bot',
            'test': 'foo_test/bar/baz',
            'revision': 1375315200,
            'value': '100.0',
            'error': '5.0',
            'masterid': 'chromium.webkit',
            'buildername': 'Builder',
            'buildnumber': 10,
            'supplemental_columns': {
                'r_chromium_svn': 123456,
                'r_webkit_rev': '23456',
            },
        }
    ]
    self.assertEqual(expected_points, actual_points)


class IsEncodedJson(mox.Comparator):
  def __init__(self, expected_json):
    self._json = expected_json

  def equals(self, rhs):
    rhs_json = urllib.unquote_plus(rhs.data.replace('data=', ''))
    return sorted(json.loads(self._json)) == sorted(json.loads(rhs_json))

  def __repr__(self):
    return '<Is Request JSON %s>' % self._json


class ResultsDashboardSendDataTest(unittest.TestCase):
  """Tests related to sending requests and saving data from failed requests."""

  def setUp(self):
    super(ResultsDashboardSendDataTest, self).setUp()
    self.mox = mox.Mox()
    self.build_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(self.build_dir, results_dashboard.CACHE_DIR))
    self.cache_file_name = os.path.join(self.build_dir,
                                        results_dashboard.CACHE_DIR,
                                        results_dashboard.CACHE_FILENAME)

  def tearDown(self):
    self.mox.UnsetStubs()
    shutil.rmtree(self.build_dir)

  def _TestSendResults(self, new_data, expected_json, errors):
    """Test one call of SendResults with the given set of arguments.

    This method will fail a test case if the JSON that gets sent and the
    errors that are raised when results_dashboard.SendResults is called
    don't match the expected json and errors.

    Args:
      new_data: The new (not cached) data to send.
      expected_json_sent: A list of JSON string expected to be sent.
      errors: A list of corresponding errors expected to be received.
    """
    self.mox.UnsetStubs()
    # urllib2.urlopen is the function that's called to send data to
    # the server. Here it is replaced with a mock object which is used
    # to record the expected JSON.
    # Because the JSON expected might be equivalent without being exactly
    # equal (in the string sense), a Mox Comparator is used.
    self.mox.StubOutWithMock(urllib2, 'urlopen')
    for json_line, error in zip(expected_json, errors):
      if error:
        urllib2.urlopen(IsEncodedJson(json_line)).AndRaise(error)
      else:
        urllib2.urlopen(IsEncodedJson(json_line))
    self.mox.ReplayAll()
    results_dashboard.SendResults(new_data, 'https:/x.com', self.build_dir)
    self.mox.VerifyAll()

  def test_FailureRetried(self):
    """After failing once, the same JSON is sent the next time."""
    # First, some data is sent but it fails for some reason.
    self._TestSendResults(
        {'sample': 1},
        ['{"sample": 1}'],
        [urllib2.URLError('some reason')])

    # The next time, the old data is sent with the new data.
    self._TestSendResults(
        {'sample': 2},
        ['{"sample": 1}', '{"sample": 2}'],
        [None, None])

  def test_SuccessNotRetried(self):
    """After being successfully sent, data is not re-sent."""
    # First, some data is sent.
    self._TestSendResults(
        {'sample': 1},
        ['{"sample": 1}'],
        [None])

    # The next time, the old data is not sent with the new data.
    self._TestSendResults(
        {'sample': 2},
        ['{"sample": 2}'],
        [None])


class ResultsDashboardTest(unittest.TestCase):
  """Tests for other functions in results_dashboard."""

  # Testing private method.
  # pylint: disable=W0212
  def test_LinkAnnotation_WithData(self):
    self.assertEqual(
        ('@@@STEP_LINK@Results Dashboard@'
         'https://chromeperf.appspot.com/report'
         '?masters=MyMaster&bots=b&tests=sunspider&rev=1234@@@'),
        results_dashboard._LinkAnnotation(
            'https://chromeperf.appspot.com',
            [{
                'master': 'MyMaster',
                'bot': 'b',
                'test': 'sunspider/Total',
                'revision': 1234,
                'value': 10,
            }]))

  def test_LinkAnnotation_UnexpectedData(self):
    self.assertIsNone(results_dashboard._LinkAnnotation('', {}))


if __name__ == '__main__':
  unittest.main()
