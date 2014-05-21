#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A buildbot command for running and interpreting GTest tests."""

import fileinput
import re
import sys
from buildbot.steps import shell
from buildbot.status import builder
from buildbot.process import buildstep
from common import gtest_utils


class TestObserver(buildstep.LogLineObserver):
  """This class knows how to understand GTest test output."""
  # TestAbbrFromTestID needs to be a member function.
  # pylint: disable=R0201

  def __init__(self):
    buildstep.LogLineObserver.__init__(self)

    self.gtest_parser = gtest_utils.GTestLogParser()

    self._master_name_re = re.compile('\[Running for master: "([^"]*)"')
    self.master_name = ''

    # Some of our log lines are now big (200K).  We need to do this
    # or twisted will drop the connection and we'll misprocess the log.
    self.setMaxLineLength(1024*1024)

  def RunningTests(self):
    """Returns list of tests that appear to be currently running."""
    return self.gtest_parser.RunningTests()

  def ParsingErrors(self):
    """Returns a list of lines that have caused parsing errors"""
    return self.gtest_parser.ParsingErrors()

  def ClearParsingErrors(self):
    """Clear the current stored parsing errors."""
    self.gtest_parser.ClearParsingErrors()

  def FailedTests(self, include_fails=False, include_flaky=False):
    """Returns list of tests that failed, timed out, or didn't finish
    (crashed).

    This list will be incorrect until the complete log has been processed,
    because it will show currently running tests as having failed.

    Args:
      include_fails: If true, all failing tests with FAILS_ in their names will
          be included. Otherwise, they will only be included if they crashed or
          timed out.
      include_flaky: If true, all failing tests with FLAKY_ in their names will
          be included. Otherwise, they will only be included if they crashed or
          timed out.

    """
    return self.gtest_parser.FailedTests(include_fails=include_fails,
                                         include_flaky=include_flaky)

  def DisabledTests(self):
    """Returns the name of the disabled test (if there is only 1) or the number
    of disabled tests.
    """
    return self.gtest_parser.DisabledTests()

  def FlakyTests(self):
    """Returns the name of the flaky test (if there is only 1) or the number
    of flaky tests.
    """
    return self.gtest_parser.FlakyTests()

  def FailureDescription(self, test):
    """Returns a list containing the failure description for the given test.

    If the test didn't fail or timeout, returns [].
    """
    return self.gtest_parser.FailureDescription(test)

  def SuppressionHashes(self):
    """Returns list of suppression hashes found in the log."""
    return self.gtest_parser.SuppressionHashes()

  def Suppression(self, suppression_hash):
    """Returns a list containing the suppression for a given hash.

    If the suppression hash doesn't exist, returns [].
    """
    return self.gtest_parser.Suppression(suppression_hash)

  def outLineReceived(self, line):
    """This is called once with each line of the test log."""
    if not self.master_name:
      results = self._master_name_re.search(line)
      if results:
        self.master_name = results.group(1)

    self.gtest_parser.ProcessLine(line)


class GTestCommand(shell.ShellCommand):
  """Buildbot command that knows how to display GTest output."""
  # TestAbbrFromTestID needs to be a member function.
  # pylint: disable=R0201

  _GTEST_DASHBOARD_BASE = ("http://test-results.appspot.com"
    "/dashboards/flakiness_dashboard.html")

  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.test_observer = TestObserver()
    self.addLogObserver('stdio', self.test_observer)

  def evaluateCommand(self, cmd):
    shell_result = shell.ShellCommand.evaluateCommand(self, cmd)
    if shell_result is builder.SUCCESS:
      if (len(self.test_observer.ParsingErrors()) or
          len(self.test_observer.FailedTests()) or
          len(self.test_observer.SuppressionHashes())):
        return builder.WARNINGS
    return shell_result

  def finished(self, results):
    if self.test_observer.ParsingErrors():
      # Generate a log file containing the list of errors.
      self.addCompleteLog('log parsing error(s)',
          '\n'.join(self.test_observer.ParsingErrors()))
      self.test_observer.ClearParsingErrors()
    return shell.ShellCommand.finished(self, results)

  def getText(self, cmd, results):
    basic_info = self.describe(True)
    disabled = self.test_observer.DisabledTests()
    if disabled:
      basic_info.append('%s disabled' % str(disabled))

    flaky = self.test_observer.FlakyTests()
    if flaky:
      basic_info.append('%s flaky' % str(flaky))

    failed_test_count = len(self.test_observer.FailedTests())

    if failed_test_count == 0:
      if results == builder.SUCCESS:
        return basic_info
      elif results == builder.WARNINGS:
        return basic_info + ['warnings']

    if self.test_observer.RunningTests():
      basic_info += ['did not complete']

    if failed_test_count:
      failure_text = ['failed %d' % failed_test_count]
      if self.test_observer.master_name:
        # Include the link to the flakiness dashboard
        failure_text.append('<div class="BuildResultInfo">')
        failure_text.append('<a href="%s#master=%s&testType=%s'
                            '&tests=%s">' % (
            self._GTEST_DASHBOARD_BASE, self.test_observer.master_name,
            self.describe(True)[0],
            ','.join(self.test_observer.FailedTests())))
        failure_text.append('Flakiness dashboard')
        failure_text.append('</a>')
        failure_text.append('</div>')
    else:
      failure_text = ['crashed or hung']
    return basic_info + failure_text

  def TestAbbrFromTestID(self, testid):
    """Split the test's individual name from GTest's full identifier.
    The name is assumed to be everything after the final '.', if any.
    The name-cleansing logic from:
      buildbot.status.build.BuildStatus.generateLogfileName()
    ... is pre-applied here to remove any URL-defeating '/' characters.
    """
    return re.sub(r'[^\w\.\-]', '_', testid.split('.')[-1])

  def createSummary(self, log):
    observer = self.test_observer
    for failure in sorted(observer.FailedTests()):
      # GTest test identifiers are of the form TestCase.TestName. We display
      # the test names only.  Unfortunately, addCompleteLog uses the name as
      # both link text and part of the text file name, so we can't incude
      # HTML tags such as <abbr> in it.
      self.addCompleteLog(self.TestAbbrFromTestID(failure),
                          '\n'.join(observer.FailureDescription(failure)))
    for suppression_hash in sorted(observer.SuppressionHashes()):
      self.addCompleteLog(suppression_hash,
                          '\n'.join(observer.Suppression(suppression_hash)))


class GTestFullCommand(GTestCommand):
  def TestAbbrFromTestID(self, testid):
    """
    Return the full TestCase.TestName ID, with the name-cleansing logic from:
      buildbot.status.build.BuildStatus.generateLogfileName()
    ... pre-applied here to remove any URL-defeating '/' characters.
    """
    return re.sub(r'[^\w\.\-]', '_', testid)


def Main():
  observer = TestObserver()
  for line in fileinput.input():
    observer.outLineReceived(line)
  print 'Failed tests:\n'
  for failed_test in observer.FailedTests(True, True):
    for fail_line in observer.FailureDescription(failed_test):
      print fail_line.strip()
    print ''
  return 0


if '__main__' == __name__:
  sys.exit(Main())
