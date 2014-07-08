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


class IsEncodedJson(mox.Comparator):
  def __init__(self, expected_json):
    self._json = expected_json

  def equals(self, rhs):
    rhs_json = urllib.unquote_plus(rhs.data.replace('data=', ''))
    return sorted(json.loads(self._json)) == sorted(json.loads(rhs_json))

  def __repr__(self):
    return '<Is Request JSON %s>' % self._json


class ResultsDashboardTest(unittest.TestCase):
  def setUp(self):
    super(ResultsDashboardTest, self).setUp()
    self.mox = mox.Mox()
    self.build_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(self.build_dir, results_dashboard.CACHE_DIR))
    self.cache_filename = os.path.join(self.build_dir,
                                       results_dashboard.CACHE_DIR,
                                       results_dashboard.CACHE_FILENAME)

  def tearDown(self):
    self.mox.UnsetStubs()
    shutil.rmtree(self.build_dir)

  def _SendResults(self, send_results_args, expected_new_json, errors,
                       mock_timestamp=False, webkit_master=False):
    """Test one call of SendResults with the given set of arguments.

    Args:
      send_results_args: The list of arguments to pass to SendResults.
      expected_new_json: A list of JSON string expected to be sent.
      errors: A list of corresponding errors expected to be received
          (Each item in the list is either a string or None.)
      mock_timestamp: Whether to stub out datetime with FakeDateTime().
      webkit_master: Whether GetActiveMaster should give the webkit master.

    This method will fail a test case if the JSON that gets sent and the
    errors that are raised when results_dashboard.SendResults is called
    don't match the expected json and errors.
    """
    # Unsetting stubs required here for multiple calls from same test.
    self.mox.UnsetStubs()
    self.mox.StubOutWithMock(slave_utils, 'GetActiveMaster')
    if webkit_master:
      slave_utils.GetActiveMaster().AndReturn('ChromiumWebkit')
    else:
      slave_utils.GetActiveMaster().AndReturn('ChromiumPerf')
    if mock_timestamp:
      self.mox.StubOutWithMock(datetime, 'datetime')
      datetime.datetime.utcnow().AndReturn(FakeDateTime())
    # urllib2.urlopen is the function that's called to send data to
    # the server. Here it is replaced with a mock object which is used
    # to record the expected JSON.
    # Because the JSON expected might be equivalent without being exactly
    # equal (in the string sense), a Mox Comparator is used.
    self.mox.StubOutWithMock(urllib2, 'urlopen')
    for json_line, error in zip(expected_new_json, errors):
      if error:
        urllib2.urlopen(IsEncodedJson(json_line)).AndRaise(error)
      else:
        urllib2.urlopen(IsEncodedJson(json_line))
    self.mox.ReplayAll()
    results_dashboard.SendResults(*send_results_args)
    self.mox.VerifyAll()

  def test_SingleLogLine(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_SupplementalColumns(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890', self.build_dir,
        {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
            'r_foo': 'SHA1',
            'r_bar': 'SHA2',
        }]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
            'r_foo': 'SHA1',
            'r_bar': 'SHA2',
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_UnitsLogLine(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456", '
         ' "v8_rev": "2345", "units": "ms"}',
         '{"traces": {"bam": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456", '
         ' "v8_rev": "2345", "units": ""}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'units': 'ms',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }},{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/bam',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_ImportantLogLine(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"one": ["1.0", "5.0"], "two": ["2.0", "0.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345", "units": "ms", '
         '"important": ["one"]}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/one',
        'revision': 12345,
        'value': '1.0',
        'error': '5.0',
        'units': 'ms',
        'important': True,
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }},{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/two',
        'revision': 12345,
        'value': '2.0',
        'error': '0.0',
        'units': 'ms',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_MultipleLogLines(self):
    args = [
        'bar-summary.dat', [
            '{"traces": {"baz": ["100.0", "5.0"]},'
            ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
            ' "v8_rev": "2345"}',
            '{"traces": {"box": ["101.0", "4.0"]},'
            ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
            ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }}, {
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/box',
        'revision': 12345,
        'value': '101.0',
        'error': '4.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_ModifiedTraceNames(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"bar": ["100.0", "5.0"], "bar_ref": ["99.0", "2.0"],'
         ' "baz/y": ["101.0", "3.0"], "notchanged": ["102.0", "1.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }},{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/ref',
        'revision': 12345,
        'value': '99.0',
        'error': '2.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }}, {
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz_y',
        'revision': 12345,
        'value': '101.0',
        'error': '3.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }},{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/notchanged',
        'revision': 12345,
        'value': '102.0',
        'error': '1.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
    }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_MultiValueRowUpload(self):
    args = [
        'my_endure_graph-summary.dat',
        ['{"traces": {'
             '"total_dom_nodes": [["10", "123"], ["20.5", "234"]],'
             '"event_listeners": [["10", "12"], ["20.5", "40"]]},'
         ' "rev": "12345",'
         ' "webkit_rev": "6789",'
         ' "webrtc_rev": "3456",'
         ' "v8_rev": "2345",'
         ' "units": "count",'
         ' "units_x": "seconds",'
         ' "stack": false}'],
        'linux-release',
        'endure/test_name',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'Linux (1)',
        '1234',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'endure/test_name/my_endure_graph/total_dom_nodes',
        'revision': 12345,
        'data': [['10', '123'], ['20.5', '234']],
        'masterid': 'chromium.perf',
        'buildername': 'Linux (1)',
        'buildnumber': '1234',
        'units': 'count',
        'units_x': 'seconds',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345'
    }}, {
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'endure/test_name/my_endure_graph/event_listeners',
        'revision': 12345,
        'data': [['10', '12'], ['20.5', '40']],
        'masterid': 'chromium.perf',
        'buildername': 'Linux (1)',
        'buildnumber': '1234',
        'units': 'count',
        'units_x': 'seconds',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345'
    }}])]
    errors = [None, None]
    self._SendResults(args, expected_new_json, errors)

  def test_ByUrlGraph(self):
    args = [
        'bar_by_url-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         '"v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)

  def test_GitHashToTimestamp(self):
    args = [
        'mean_frame_time-summary.dat',
        ['{"traces": {"mean_frame_time": ["77.0964285714", "138.142773233"]},'
         ' "rev": "2eca27b067e3e57c70e40b8b95d0030c5d7c1a7f",'
         ' "webkit_rev": "bf9aa8d62561bb2e4d7bc09e9d9e8c6a665ddc88",'
         ' "webrtc_rev": "bf9aa8d62561bb2e4d7bc09e9d9e8c6a665ddc86",'
         ' "v8_rev": "bf9aa8d62561bb2e4d7bc09e9d9e8c6a665ddc87",'
         ' "ver": "undefined", "chan": "undefined", "units": "ms",'
         ' "important": ["mean_frame_time"]}'],
        'linux-release',
        'smoothness_measurement',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'Linux (1)',
        '1234',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'smoothness_measurement/mean_frame_time',
        'revision': 1375315200,
        'value': '77.0964285714',
        'error': '138.142773233',
        'masterid': 'chromium.perf',
        'buildername': 'Linux (1)',
        'buildnumber': '1234',
        'important': True,
        'units': 'ms',
        'supplemental_columns': {
            'r_chromium': '2eca27b067e3e57c70e40b8b95d0030c5d7c1a7f',
            'r_webkit_rev': 'bf9aa8d62561bb2e4d7bc09e9d9e8c6a665ddc88',
            'r_webrtc_rev': 'bf9aa8d62561bb2e4d7bc09e9d9e8c6a665ddc86',
            'r_v8_rev': 'bf9aa8d62561bb2e4d7bc09e9d9e8c6a665ddc87',
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors, mock_timestamp=True)

  def test_WebkitUsesTimestamp(self):
    args = [
        'mean_frame_time-summary.dat',
        ['{"traces": {"mean_frame_time": ["77.0964285714", "138.142773233"]},'
         ' "rev": "12345",'
         ' "webkit_rev": "23456",'
         ' "webrtc_rev": "3456",'
         ' "v8_rev": "34567",'
         ' "ver": "undefined", "chan": "undefined", "units": "ms",'
         ' "important": ["mean_frame_time"]}'],
        'linux-release',
        'smoothness_measurement',
        'https://chrome-perf.googleplex.com',
        'chromium.webkit',
        'Linux (1)',
        '1234',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumWebkit',
        'bot': 'linux-release',
        'test': 'smoothness_measurement/mean_frame_time',
        'revision': 1375315200,
        'value': '77.0964285714',
        'error': '138.142773233',
        'masterid': 'chromium.webkit',
        'buildername': 'Linux (1)',
        'buildnumber': '1234',
        'important': True,
        'units': 'ms',
        'supplemental_columns': {
            'r_chromium_svn': 12345,
            'r_webkit_rev': '23456',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '34567',
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors, mock_timestamp=True,
                      webkit_master=True)

  def test_FailureRetried(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }}])]
    errors = [urllib2.URLError('reason')]
    self._SendResults(args, expected_new_json, errors)
    args2 = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["101.0", "6.0"]},'
         ' "rev": "12346", "webkit_rev": "6790", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json.append(json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12346,
        'value': '101.0',
        'error': '6.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6790',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }
    }]))
    errors = [None, None]
    self._SendResults(args2, expected_new_json, errors)

  def test_SuccessNotRetried(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }}])]
    errors = [None]
    self._SendResults(args, expected_new_json, errors)
    args2 = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["101.0", "6.0"]},'
         ' "rev": "12346", "webkit_rev": "6790", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json2 = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12346,
        'value': '101.0',
        'error': '6.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6790',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }
    }])]
    errors = [None]
    self._SendResults(args2, expected_new_json2, errors)

  def test_FailureCached(self):
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["100.0", "5.0"]},'
         ' "rev": "12345", "webkit_rev": "6789", "webrtc_rev": "3456",'
         ' "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }}])]
    errors = [urllib2.URLError('reason')]
    self._SendResults(args, expected_new_json, errors)
    cache_file = open(self.cache_filename, 'rb')
    actual_cache = cache_file.read()
    cache_file.close()
    # Compare the dicts loaded from the JSON instead of the actual JSON string,
    # because the order of the fields in the string doesn't matter.
    self.assertEqual(json.loads(expected_new_json[0]), json.loads(actual_cache))

  def test_NoResendAfterMultipleErrors(self):
    previous_lines = '\n'.join([
        json.dumps([{
            'master': 'ChromiumPerf',
            'bot': 'linux-release',
            'test': 'foo/bar/baz',
            'revision': 12345,
            'value': '100.0',
            'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
            'supplemental_columns': {
                'r_webkit_rev': '6789',
                'r_webrtc_rev': '3456',
                'r_v8_rev': '2345',
            }}]),
        json.dumps([{
            'master': 'ChromiumPerf',
            'bot': 'linux-release',
            'test': 'foo/bar/baz',
            'revision': 12346,
            'value': '101.0',
            'error': '5.0',
            'masterid': 'chromium.perf',
            'buildername': 'XP Perf (1)',
            'buildnumber': '7890',
            'supplemental_columns': {
                'r_webkit_rev': '6789',
                'r_webrtc_rev': '3456',
                'r_v8_rev': '2345',
            }}]),
        json.dumps([{
            'master': 'ChromiumPerf',
            'bot': 'linux-release',
            'test': 'foo/bar/baz',
            'revision': 12347,
            'value': '99.0',
            'error': '5.0',
            'masterid': 'chromium.perf',
            'buildername': 'XP Perf (1)',
            'buildnumber': '7890',
            'supplemental_columns': {
                'r_webkit_rev': '6789',
                'r_webrtc_rev': '3456',
                'r_v8_rev': '2345',
            }}])
    ])
    cache_file = open(self.cache_filename, 'wb')
    cache_file.write(previous_lines)
    cache_file.close()
    args = [
        'bar-summary.dat',
        ['{"traces": {"baz": ["102.0", "5.0"]},'
         ' "rev": "12348", "webkit_rev": "6789", "v8_rev": "2345"}'],
        'linux-release',
        'foo',
        'https://chrome-perf.googleplex.com',
        'chromium.perf',
        'XP Perf (1)',
        '7890',
        self.build_dir,
        {}]
    expected_new_json = [json.dumps([{
        'master': 'ChromiumPerf',
        'bot': 'linux-release',
        'test': 'foo/bar/baz',
        'revision': 12345,
        'value': '100.0',
        'error': '5.0',
        'masterid': 'chromium.perf',
        'buildername': 'XP Perf (1)',
        'buildnumber': '7890',
        'supplemental_columns': {
            'r_webkit_rev': '6789',
            'r_webrtc_rev': '3456',
            'r_v8_rev': '2345',
        }}])]
    errors = [urllib2.URLError('reason')]
    self._SendResults(args, expected_new_json, errors)
    cache_file = open(self.cache_filename, 'rb')
    actual_cache_lines = [l.strip() for l in cache_file.readlines()]
    cache_file.close()
    self.assertEqual(4, len(actual_cache_lines))
    for line in previous_lines.split('\n') + expected_new_json:
      self.assertTrue(line in actual_cache_lines)


if __name__ == '__main__':
  unittest.main()
