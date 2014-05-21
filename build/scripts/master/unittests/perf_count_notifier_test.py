#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0611
import unittest
import mock

from buildbot.status.builder import FAILURE, SUCCESS

from master import build_utils
from master.chromium_notifier import ChromiumNotifier
from master.perf_count_notifier import PerfCountNotifier

import twisted.internet.defer

# Sample test status results.
# Based on log_parser/process_log.py PerformanceChangesAsText() function,
# we assume that PERF_REGRESS (if any) appears before PERF_IMPROVE.
TEST_STATUS_TEXT = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: time/t '
    '(89.07%) PERF_IMPROVE: fps/video (5.40%) </div>')

TEST_STATUS_TEXT_COUNTER = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: fps/video '
    '(3.0%) PERF_IMPROVE: time/t (44.07%) </div>')

TEST_STATUS_TEXT_2 = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: time/t2 '
    '(89.07%) PERF_IMPROVE: fps/video2 (5.40%) </div>')

TEST_STATUS_TEXT_EXCEPTION = ('media_tests_av_perf exception')

TEST_STATUS_MULTI_REGRESS = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: time/t '
    '(89.07%), fps/video (5.40%), fps/video2 (5.40%) </div>')

TEST_STATUS_MULTI_IMPROVE = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_IMPROVE: time/t '
    '(89.07%), fps/video (5.40%), fps/video2 (5.40%) </div>')

TEST_STATUS_MULTI_REGRESS_IMPROVE = (
    'media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS: time/t '
    '(89.07%), fps/video (5.40%), fps/video2 (5.40%) PERF_IMPROVE: cpu/t '
    '(44.07%), cpu/t2 (3.0%) </div>')


def getBuildStatusMock(name):
  """Mocks a build status with a name as the parameter."""
  builder = mock.Mock()
  builder.getName.return_value = name

  build_status = mock.Mock()
  build_status.getBuilder.return_value = builder
  build_status.getSourceStamp.return_value = None
  build_status.getResponsibleUsers.return_value = ''
  build_status.getChanges.return_value = ''
  return build_status


class PerfCountNotifierTest(unittest.TestCase):

  def setUp(self):
    self.email_sent = False
    self.notifier = PerfCountNotifier(
        fromaddr='buildbot@test',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.',
        step_names='test_tests',
        minimum_count=3)
    self.old_getName = None
    self.mockDefaultFunctions()

  def tearDown(self):
    self.resetMockDefaultFunctions()

  def mockDefaultFunctions(self):
    self.old_getName = ChromiumNotifier.getName
    ChromiumNotifier.getName = self.getNameMock

  def resetMockDefaultFunctions(self):
    ChromiumNotifier.getName = self.old_getName

  def getNameMock(self, step_status):
    """Mocks the getName which returns the build_status step name."""
    return self.notifier.step_names[0]

  def getResultCount(self, result_name):
    """Returns the number of times result_name has been stored."""
    return self.notifier.recent_results.GetCount(result_name)

  def testSuccessIsNotInteresting(self):
    """Test success step is not interesting."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [SUCCESS]
    for _ in range(self.notifier.minimum_count):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))

  def testIsInterestingAfterMinimumResults(self):
    """Test step is interesting only after minimum consecutive results."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetByCounterResults(self):
    """Test step is not interesting if a counter result appears."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    # Reset the counters by having counter results.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_COUNTER)
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Now check that we need to count back from the start.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetBySuccess(self):
    """Test step count reset after a successful pass."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    # Reset the counters by having a success step.
    results = [SUCCESS]
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Now check that we need to count back from the start.
    results = [1]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingException(self):
    """Test step is interesting when step has exception."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_EXCEPTION)
    results = [FAILURE]
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testNotificationOnce(self):
    """Test isInsteresting happens only once."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Force expiration of notifications
    self.notifier.notifications.expiration_time = -1
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetByOtherResults(self):
    """Test isInsteresting resets after different results appear."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    # Reset the counters by having other results.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_2)
    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))
    # Now check that we need to count back from the start.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testCountIsCorrectMultipleRegressOnly(self):
    """Test count of multiple REGRESS only is correct."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_MULTI_REGRESS)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)

    self.assertEqual(self.getResultCount('REGRESS time/t test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('REGRESS fps/video test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(
        self.getResultCount('REGRESS fps/video2 test_build'),
        self.notifier.minimum_count)

  def testCountIsCorrectMultipleImproveOnly(self):
    """Test count of multiple IMPROVE only is correct."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_MULTI_IMPROVE)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)

    self.assertEqual(self.getResultCount('IMPROVE time/t test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE fps/video test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(
        self.getResultCount('IMPROVE fps/video2 test_build'),
        self.notifier.minimum_count)

  def testCountIsCorrectMultipleRegressImprove(self):
    """Test count of multiple REGRESS and IMPROVE is correct."""
    build_status = getBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_MULTI_REGRESS_IMPROVE)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)

    self.assertEqual(self.getResultCount('REGRESS time/t test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('REGRESS fps/video test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(
        self.getResultCount('REGRESS fps/video2 test_build'),
        self.notifier.minimum_count)

    self.assertEqual(self.getResultCount('IMPROVE cpu/t test_build'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE cpu/t2 test_build'),
                     self.notifier.minimum_count)

  def testEmailContext(self):
    """Tests email context contains relative failures."""
    # Needed so that callback details are retained after method call.
    twisted.internet.defer.Deferred._startRunCallbacks = mock.Mock()
    self.notifier.minimum_delay_between_alert = 0

    step_status = BuildStepStatusMock(TEST_STATUS_MULTI_REGRESS)
    build_status = getBuildStatusMock('test_build')

    self.notifier.master_status = mock.Mock()
    self.notifier.master_status.getBuildbotURL.return_value = ''

    build_utils.EmailableBuildTable = mock.Mock(return_value='')

    results = [FAILURE]
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)
    email = self.notifier.buildMessage(builder_name='',
                                       build_status=build_status,
                                       results=results, step_name='')
    first_callback = email.callbacks[0]
    callback_args = first_callback[0][1]  # Defer.addCallBacks implementation
    email_content = callback_args[1].as_string()  # [0] is receipients
    self.assertTrue('New perf results in this email' in email_content)
    self.assertTrue('PERF_REGRESS: time/t, fps/video, fps/video2.' in
                    email_content)
    self.assertTrue('PERF_IMPROVE: cpu/t, cpu/t2.' not in email_content)

    # Check that the previous regress/improve values do not show again and the
    # new values are shown.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_2)
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)
    email = self.notifier.buildMessage(builder_name='',
                                       build_status=build_status,
                                       results=results, step_name='')
    first_callback = email.callbacks[0]
    callback_args = first_callback[0][1]  # Defer.addCallBacks implementation
    email_content = callback_args[1].as_string()  # [0] is receipients

    self.assertTrue('New perf results in this email' in email_content)
    self.assertTrue('PERF_REGRESS: time/t, fps/video, fps/video2.' not in
                    email_content)
    self.assertTrue('PERF_REGRESS: time/t2.' in email_content)
    self.assertTrue('PERF_IMPROVE: fps/video2.' in email_content)

  def testResultsForDifferentBuilders(self):
    """Tests that results are unique per builder."""
    build_linux = getBuildStatusMock('test_linux')
    build_win = getBuildStatusMock('test_win')
    step_status = BuildStepStatusMock(TEST_STATUS_MULTI_IMPROVE)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_linux, step_status, results)
      self.notifier.isInterestingStep(build_win, step_status, results)

    # Check results store the builder names
    self.assertEqual(self.getResultCount('IMPROVE time/t test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE time/t test_win'),
                     self.notifier.minimum_count)

    # Reset only build_linux results
    results = [SUCCESS]
    self.assertFalse(self.notifier.isInterestingStep(
        build_linux, step_status, results))

    # Check build_win results are intact.
    self.assertEqual(self.getResultCount('IMPROVE time/t test_linux'), 0)
    self.assertEqual(self.getResultCount('IMPROVE time/t test_win'),
                     self.notifier.minimum_count)

    results = [FAILURE]
    # Add build_lin results
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_linux, step_status, results)

    # Check results store the builder names
    self.assertEqual(self.getResultCount('IMPROVE time/t test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE time/t test_win'),
                     self.notifier.minimum_count)

    # Reset only build_win results
    results = [SUCCESS]
    self.assertFalse(self.notifier.isInterestingStep(
        build_win, step_status, results))

    # Check build_lin results are intact.
    self.assertEqual(self.getResultCount('IMPROVE time/t test_win'), 0)
    self.assertEqual(self.getResultCount('IMPROVE time/t test_linux'),
                     self.notifier.minimum_count)


class BuildStepStatusMock(mock.Mock):
  def __init__(self, text):
    self.text = text
    mock.Mock.__init__(self)

  def getText(self):
    return [self.text]


if __name__ == '__main__':
  unittest.main()
