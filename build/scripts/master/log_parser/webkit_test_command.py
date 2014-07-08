# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A buildbot command for running and interpreting webkit layout tests."""

import re

from buildbot.process import buildstep
from buildbot.steps import shell
from buildbot.status import builder


def _BasenameFromPath(path):
  """Extracts the basename of either a Unix- or Windows- style path,
  assuming it contains either \ or / but not both.
  """
  short_path = path.split('\\')[-1]
  short_path = short_path.split('/')[-1]
  return short_path


class TestObserver(buildstep.LogLineObserver):
  """This class knows how to understand webkit test output."""

  def __init__(self):
    buildstep.LogLineObserver.__init__(self)

    # State tracking for log parsing.
    self._current_category = ''

    # List of unexpectedly failing tests.
    self.failed_tests = []

    # List of unexpectedly passing tests.
    self.unexpected_passing = []

    # List of flaky tests that we expected to be non-flaky.
    self.unexpected_flaky = []

    # Counts of all fixable tests and those that were skipped. These will
    # be unchanged if log-file parsing fails.
    self.fixable_all = '??'
    self.fixable_skipped = 0

    # Headers and regular expressions for parsing logs.  We don't
    # distinguish among failures, crashes, and hangs in the display.
    self._passing_start = re.compile('Expected to .+, but passed')
    self._regressions_start = re.compile('Regressions: [Uu]nexpected .+')
    self._flaky_start = re.compile('[Uu]nexpected flakiness: .+')

    self._section_end = '-' * 78
    self._summary_end = '=> Tests '

    self._test_path_line = re.compile('  (\S+)')

    self._summary_start = re.compile(
        '=> Tests to be fixed \((\d+)\):')
    self._summary_skipped = re.compile('(\d+) skipped')

    self._master_name_re = re.compile('--master-name ([^ ]*)')
    self.master_name = ''

  def outLineReceived(self, line):
    """This is called once with each line of the test log."""

    results = self._master_name_re.search(line)
    if results:
      self.master_name = results.group(1)

    results = self._passing_start.search(line)
    if results:
      self._current_category = 'passing'
      return

    results = self._flaky_start.search(line)
    if results:
      self._current_category = 'flaky'
      return

    results = self._regressions_start.search(line)
    if results:
      self._current_category = 'regressions'
      return

    results = self._summary_start.search(line)
    if results:
      self._current_category = 'summary'
      try:
        self.fixable_all = int(results.group(1))
      except ValueError:
        pass
      return

    # Are we starting or ending a new section?
    # Check this after checking for the start of the summary section.
    if (line.startswith(self._section_end) or
        line.startswith(self._summary_end)):
      self._current_category = ''
      return

    # Are we looking at the summary section?
    if self._current_category == 'summary':
      results = self._summary_skipped.search(line)
      if results:
        try:
          self.fixable_skipped = int(results.group(1))
        except ValueError:
          pass
      return

    self.appendMatchingTest(line, 'regressions', self.failed_tests)
    self.appendMatchingTest(line, 'passing', self.unexpected_passing)
    self.appendMatchingTest(line, 'flaky', self.unexpected_flaky)


  def appendMatchingTest(self, line, category, test_list):
    if self._current_category == category:
      results = self._test_path_line.search(line)
      if results:
        test_list.append(results.group(1))

class WebKitCommand(shell.ShellCommand):
  """Buildbot command that knows how to display layout test output."""

  _LAYOUT_TEST_DASHBOARD_BASE = ("http://test-results.appspot.com"
    "/dashboards/flakiness_dashboard.html")

  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.test_observer = TestObserver()
    self.addLogObserver('stdio', self.test_observer)
    # The maximum number of tests to list on the buildbot waterfall, for
    # regressions and unexpectedly passing tests.
    self._MAX_FAIL_LIST = 25
    self._MAX_PASS_LIST = 10

  def evaluateCommand(self, cmd):
    """Decide whether the command was SUCCESS, WARNINGS, or FAILURE.

    Tests unexpectedly passing is WARNINGS.  Unexpected failures is FAILURE.
    """
    if cmd.rc != 0:
      return builder.FAILURE
    if (len(self.test_observer.unexpected_passing) or
        len(self.test_observer.unexpected_flaky)):
      return builder.WARNINGS
    return builder.SUCCESS

  def _BuildTestList(self, tests, maxlen, description):
    """Returns a list of test links to be shown in the waterfall.

    Args:
      tests: list of test paths to show
      maxlen: show at most this many, with '...and more' appended if needed
      description: a few words describing the tests, e.g. 'failed'
    """
    if not len(tests):
      return []

    full_desc = ['%s %d' % (description, len(tests))]
    full_desc.append('<div class="BuildResultInfo">')

    full_desc.append('<a href="%s#master=%s&tests=%s">' % (
        self._LAYOUT_TEST_DASHBOARD_BASE, self.test_observer.master_name,
        ','.join(sorted(tests))))

    # Display test names, with full paths as tooltips.
    name_path_pairs = [(_BasenameFromPath(path), path)
        for path in tests[:maxlen]]
    for name, path in sorted(name_path_pairs):
      full_desc.append('<abbr title="%s">%s</abbr>' % (path, name))
      full_desc.append('<br>')
    if len(tests) > maxlen:
      full_desc.append('...and more')

    full_desc.append('</a>')
    full_desc.append('</div>')
    return full_desc

  def getText(self, cmd, results):
    basic_info = self.describe(True)
    basic_info.extend(['%s fixable' % self.test_observer.fixable_all,
                       '(%s skipped)' % self.test_observer.fixable_skipped])

    if results == builder.SUCCESS:
      return basic_info
    elif results == builder.WARNINGS:
      failure_text = self._BuildTestList(self.test_observer.unexpected_passing,
                                         self._MAX_PASS_LIST,
                                         'unexpected pass')
    else:
      failures = self.test_observer.failed_tests
      if len(failures) > 0:
        failure_text = self._BuildTestList(failures,
                                           self._MAX_FAIL_LIST,
                                           'failed')
      else:
        failure_text = ['crashed or hung']

    # Include flaky results in the failure list whether we turn the bot
    # red or orange.
    failure_text += self._BuildTestList(self.test_observer.unexpected_flaky,
                                        self._MAX_PASS_LIST,
                                        'unexpected flaky')
    return basic_info + failure_text
