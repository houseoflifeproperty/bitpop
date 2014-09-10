#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for functions in runtest.py."""

import unittest

import test_env  # pylint: disable=W0403,W0611

import mock
from slave import runtest


class FakeLogProcessor(object):
  """A fake log processor to use in the test below."""

  def __init__(self, output):
    self._output = output

  def PerformanceLogs(self):
    return self._output


class GetDataFromLogProcessorTest(unittest.TestCase):
  """Tests related to functions which convert data format."""

  def setUp(self):
    super(GetDataFromLogProcessorTest, self).setUp()

  # Testing private method _GetDataFromLogProcessor.
  # pylint: disable=W0212
  def test_GetDataFromLogProcessor_BasicCase(self):
    """Tests getting of result data from a LogProcessor object."""
    log_processor = FakeLogProcessor({
        'graphs.dat': ['[{"name": "my_graph"}]'],
        'my_graph-summary.dat': ['{"traces": {"x": [1, 0]}, "rev": 123}'],
    })

    # Note that the 'graphs.dat' entry is ignored.
    self.assertEqual(
        {'my_graph': {'traces': {'x': [1, 0]}, 'rev': 123}},
        runtest._GetDataFromLogProcessor(log_processor))

  def test_GetDataFromLogProcessor_OneGraphMultipleLines(self):
    log_processor = FakeLogProcessor({
        'graph-summary.dat': [
            '{"traces": {"x": [1, 0]}, "rev": 123}',
            '{"traces": {"y": [1, 0]}, "rev": 123}',
        ]
    })

    # We always expect the length of the lines list for each graph to be 1.
    # If it doesn't meet this expectation, ignore that graph.
    self.assertEqual({}, runtest._GetDataFromLogProcessor(log_processor))

  def test_GetDataFromLogProcessor_InvalidJson(self):
    log_processor = FakeLogProcessor({
        'graph-summary.dat': ['this string is not valid json']
    })
    self.assertEqual({}, runtest._GetDataFromLogProcessor(log_processor))


class SendResultsToDashboardTest(unittest.TestCase):
  """Tests related to sending requests and saving data from failed requests."""

  def setUp(self):
    super(SendResultsToDashboardTest, self).setUp()

  # Testing private method _GetDataFromLogProcessor.
  # Also, this test method doesn't reference self.
  # pylint: disable=W0212,R0201
  @mock.patch('slave.runtest._GetDataFromLogProcessor')
  @mock.patch('slave.results_dashboard.MakeListOfPoints')
  @mock.patch('slave.results_dashboard.SendResults')
  def test_SendResultsToDashboard_SimpleCase(
      self, SendResults, MakeListOfPoints, GetDataFromLogProcessor):
    """Tests that the right methods get called in _SendResultsToDashboard."""
    # Since this method just tests that certain methods get called when
    # a call to _SendResultsDashboard is made, the data used below is arbitrary.
    fake_charts_data = {'chart': {'traces': {'x': [1, 0]}, 'rev': 1000}}
    fake_points_data = [{'test': 'master/bot/chart/x', 'revision': 1000}]
    fake_results_tracker = object()
    GetDataFromLogProcessor.return_value = fake_charts_data
    MakeListOfPoints.return_value = fake_points_data

    runtest._SendResultsToDashboard(
        fake_results_tracker, 'linux', 'sunspider', 'http://x.com', 'builddir',
        'my.master', 'Builder', 123, 'columns_file', extra_columns={})

    # First a function is called to get data from the log processor.
    GetDataFromLogProcessor.assert_called_with(fake_results_tracker)

    # Then the data is re-formatted to a format that the dashboard accepts.
    MakeListOfPoints.assert_called_with(
        fake_charts_data, 'linux', 'sunspider', 'my.master', 'Builder', 123, {})

    # Then a function is called to send the data (and any cached data).
    SendResults.assert_called_with(
        fake_points_data, 'http://x.com', 'builddir')


if __name__ == '__main__':
  unittest.main()
