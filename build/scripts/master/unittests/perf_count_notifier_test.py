#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0611
import unittest
import mock
import re

from buildbot.status.builder import FAILURE, SUCCESS

from master import build_utils
from master.chromium_notifier import ChromiumNotifier
from master.perf_count_notifier import PerfCountNotifier


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


def GetBuildStatusMock(name):
  """Mocks a build status with a name as the parameter."""
  builder = mock.Mock()
  builder.getName.return_value = name

  build_status = mock.Mock()
  build_status.getBuilder.return_value = builder
  build_status.getSourceStamp.return_value = None
  build_status.getResponsibleUsers.return_value = ''
  build_status.getChanges.return_value = ''
  build_status.getSteps.return_value = []
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
    self.notifier.GenStepBox = lambda x, y, z: ''
    self.notifier.BuildEmailObject = lambda a, b, c, d, e : b
    self.notifier.master_status = mock.Mock()
    self.notifier.master_status.getBuildbotURL.return_value = ''
    build_utils.EmailableBuildTable = mock.Mock(return_value='')

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
    build_status = GetBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [SUCCESS]
    for _ in range(self.notifier.minimum_count):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))

  def testIsInterestingAfterMinimumResults(self):
    """Test step is interesting only after minimum consecutive results."""
    build_status = GetBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetByCounterResults(self):
    """Test step is not interesting if a counter result appears."""
    build_status = GetBuildStatusMock('test_build')
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
    build_status = GetBuildStatusMock('test_build')
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
    build_status = GetBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_EXCEPTION)
    results = [FAILURE]
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testNotificationOnce(self):
    """Test isInsteresting happens until email is sent."""
    build_status = GetBuildStatusMock('test_build')
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT)
    results = [FAILURE]
    for _ in range(self.notifier.minimum_count - 1):
      self.assertFalse(self.notifier.isInterestingStep(
          build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))
    self.assertTrue(self.notifier.isInterestingStep(
        build_status, step_status, results))

    builder_name = build_status.getBuilder().getName()
    self.notifier.buildMessage(builder_name=builder_name,
                               build_status=build_status,
                               results=results, step_name='')

    self.assertFalse(self.notifier.isInterestingStep(
        build_status, step_status, results))

  def testIsInterestingResetByOtherResults(self):
    """Test isInsteresting resets after different results appear."""
    build_status = GetBuildStatusMock('test_build')
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
    build_status = GetBuildStatusMock('test_build')
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
    build_status = GetBuildStatusMock('test_build')
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
    build_status = GetBuildStatusMock('test_build')
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
    self.notifier.minimum_delay_between_alert = 0
    step_status = BuildStepStatusMock(TEST_STATUS_MULTI_REGRESS)
    build_status = GetBuildStatusMock('test_build')

    results = [FAILURE]
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)

    builder_name = build_status.getBuilder().getName()
    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_status,
                                               results=results, step_name='')
    self.assertTrue(re.match('.*PERF_REGRESS.*time/t.*fps/video.*fps/video2.*',
                             email_content))
    self.assertTrue('PERF_IMPROVE' not in email_content)

    # Check that the previous regress/improve values do not show again and the
    # new values are shown.
    step_status = BuildStepStatusMock(TEST_STATUS_TEXT_2)
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_status, step_status, results)

    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_status,
                                               results=results, step_name='')
    # Assert old regressions are not valid anymore.
    for string in ['time/t</a>', 'fps/video</a>']:
      self.assertTrue(string not in email_content)
    for string in ['time/t2</a>', 'fps/video2</a>']:
      self.assertTrue(string in email_content)

    self.assertTrue(re.match('.*PERF_REGRESS.*time/t2.*'
                             'PERF_IMPROVE.*fps/video2.*', email_content))

  def testResultsForDifferentBuilders(self):
    """Tests that results are unique per builder."""
    build_linux = GetBuildStatusMock('test_linux')
    build_win = GetBuildStatusMock('test_win')
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

  def testCombinedResultsForDifferentBuilders(self):
    """Tests email content sent when combined=True for multi builders."""
    build_linux = GetBuildStatusMock('test_linux')
    build_win = GetBuildStatusMock('test_win')
    step_status_linux = BuildStepStatusMock(TEST_STATUS_TEXT)
    step_status_win = BuildStepStatusMock(TEST_STATUS_TEXT_2)
    results = [FAILURE]
    self.notifier.combine_results = True
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_linux, step_status_linux, results)
      self.notifier.isInterestingStep(build_win, step_status_win, results)
    # Check results store the builder names
    self.assertEqual(self.getResultCount('REGRESS time/t test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE fps/video test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('REGRESS time/t2 test_win'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE fps/video2 test_win'),
                     self.notifier.minimum_count)
    # Use any builder name since combine_results should ignore that.
    builder_name = build_linux.getBuilder().getName()
    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_linux,
                                               results=results, step_name='')
    # Both win and linux results should appear in email content.
    self.assertTrue(re.match('.*PERF_REGRESS.*time/t.*PERF_IMPROVE.*'
                             'fps/video.*PERF_REGRESS.*time/t2.*PERF_IMPROVE.*'
                             'fps/video2.*', email_content))

  def testNonCombinedResultsForDifferentBuilders(self):
    """Tests email content sent when combined=False for multi builders."""
    build_linux = GetBuildStatusMock('test_linux')
    build_win = GetBuildStatusMock('test_win')
    step_status_linux = BuildStepStatusMock(TEST_STATUS_MULTI_REGRESS)
    step_status_win = BuildStepStatusMock(TEST_STATUS_MULTI_IMPROVE)
    results = [FAILURE]
    self.notifier.combine_results = False
    for _ in range(self.notifier.minimum_count):
      self.notifier.isInterestingStep(build_linux, step_status_linux, results)
      self.notifier.isInterestingStep(build_win, step_status_win, results)
    # Check results store the builder names
    self.assertEqual(self.getResultCount('REGRESS time/t test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('REGRESS fps/video test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('REGRESS fps/video2 test_linux'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE time/t test_win'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE fps/video test_win'),
                     self.notifier.minimum_count)
    self.assertEqual(self.getResultCount('IMPROVE fps/video2 test_win'),
                     self.notifier.minimum_count)
    # Check only linux results show in linux builder email
    builder_name = build_linux.getBuilder().getName()
    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_linux,
                                               results=results, step_name='')
    self.assertTrue(re.match('.*PERF_REGRESS.*time/t.*fps/video.*fps/video2.*',
                             email_content))
    self.assertTrue('PERF_IMPROVE' not in email_content)
    # Check that email should not send again,
    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_linux,
                                               results=results, step_name='')
    self.assertTrue('PERF_IMPROVE' not in email_content and
                    'PERF_REGRESS' not in email_content)
    # Check win results show in win builder email separately
    builder_name = build_win.getBuilder().getName()
    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_win,
                                               results=results, step_name='')
    self.assertTrue(re.match('.*PERF_IMPROVE.*time/t.*fps/video.*fps/video2.*',
                             email_content))
    self.assertTrue('PERF_REGRESS' not in email_content)
    # Check that email should not send again,
    email_content = self.notifier.buildMessage(builder_name=builder_name,
                                               build_status=build_win,
                                               results=results, step_name='')
    self.assertTrue('PERF_IMPROVE' not in email_content and
                    'PERF_REGRESS' not in email_content)


def BuildStepStatusMock(text):
  ret = mock.Mock()
  ret.getText.return_value = [text]
  return ret


if __name__ == '__main__':
  unittest.main()
