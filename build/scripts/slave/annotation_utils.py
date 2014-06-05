# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generates annotated output.

TODO(stip): Move the gtest_utils gtest parser selection code from runtest.py
to here.
TODO(stip): Move the perf dashboard code from runtest.py to here.
"""

import re

from slave import process_log_utils
from slave import slave_utils


def getText(result, observer, name):
  """Generate a text summary for the waterfall.

  Updates the waterfall with any unusual test output, with a link to logs of
  failed test steps.
  """
  GTEST_DASHBOARD_BASE = ('http://test-results.appspot.com'
                          '/dashboards/flakiness_dashboard.html')

  # TODO(xusydoc): unify this with gtest reporting below so getText() is
  # less confusing
  if hasattr(observer, 'PerformanceSummary'):
    basic_info = [name]
    summary_text = ['<div class="BuildResultInfo">']
    summary_text.extend(observer.PerformanceSummary())
    summary_text.append('</div>')
    return basic_info + summary_text

  # basic_info is an array of lines to display on the waterfall.
  basic_info = [name]

  disabled = observer.DisabledTests()
  if disabled:
    basic_info.append('%s disabled' % str(disabled))

  flaky = observer.FlakyTests()
  if flaky:
    basic_info.append('%s flaky' % str(flaky))

  failed_test_count = len(observer.FailedTests())
  if failed_test_count == 0:
    if result == process_log_utils.SUCCESS:
      return basic_info
    elif result == process_log_utils.WARNINGS:
      return basic_info + ['warnings']

  if observer.RunningTests():
    basic_info += ['did not complete']

  # TODO(xusydoc): see if 'crashed or hung' should be tracked by RunningTests().
  if failed_test_count:
    failure_text = ['failed %d' % failed_test_count]
    if observer.master_name:
      # Include the link to the flakiness dashboard.
      failure_text.append('<div class="BuildResultInfo">')
      failure_text.append('<a href="%s#master=%s&testType=%s'
                          '&tests=%s">' % (GTEST_DASHBOARD_BASE,
                                           observer.master_name,
                                           name,
                                           ','.join(observer.FailedTests())))
      failure_text.append('Flakiness dashboard')
      failure_text.append('</a>')
      failure_text.append('</div>')
  else:
    failure_text = ['crashed or hung']
  return basic_info + failure_text


def annotate(test_name, result, results_tracker, full_name=False,
             perf_dashboard_id=None):
  """Given a test result and tracker, update the waterfall with test results."""

  # Always print raw exit code of the subprocess. This is very helpful
  # for debugging, especially when one gets the "crashed or hung" message
  # with no output (exit code can have some clues, especially on Windows).
  print 'exit code (as seen by runtest.py): %d' % result

  get_text_result = process_log_utils.SUCCESS

  for failure in sorted(results_tracker.FailedTests()):
    if full_name:
      testabbr = re.sub(r'[^\w\.\-]', '_', failure)
    else:
      testabbr = re.sub(r'[^\w\.\-]', '_', failure.split('.')[-1])
    slave_utils.WriteLogLines(testabbr,
                              results_tracker.FailureDescription(failure))
  for suppression_hash in sorted(results_tracker.SuppressionHashes()):
    slave_utils.WriteLogLines(suppression_hash,
                              results_tracker.Suppression(suppression_hash))

  if results_tracker.ParsingErrors():
    # Generate a log file containing the list of errors.
    slave_utils.WriteLogLines('log parsing error(s)',
                              results_tracker.ParsingErrors())

    results_tracker.ClearParsingErrors()

  if hasattr(results_tracker, 'evaluateCommand'):
    parser_result = results_tracker.evaluateCommand('command')
    if parser_result > result:
      result = parser_result

  if result == process_log_utils.SUCCESS:
    if (len(results_tracker.ParsingErrors()) or
        len(results_tracker.FailedTests()) or
        len(results_tracker.SuppressionHashes())):
      print '@@@STEP_WARNINGS@@@'
      get_text_result = process_log_utils.WARNINGS
  elif result == slave_utils.WARNING_EXIT_CODE:
    print '@@@STEP_WARNINGS@@@'
    get_text_result = process_log_utils.WARNINGS
  else:
    print '@@@STEP_FAILURE@@@'
    get_text_result = process_log_utils.FAILURE

  for desc in getText(get_text_result, results_tracker, test_name):
    print '@@@STEP_TEXT@%s@@@' % desc

  if hasattr(results_tracker, 'PerformanceLogs'):
    if not perf_dashboard_id:
      raise Exception('runtest.py error: perf step specified but'
                      'no test_id in factory_properties!')
    for logname, log in results_tracker.PerformanceLogs().iteritems():
      lines = [str(l).rstrip() for l in log]
      slave_utils.WriteLogLines(logname, lines, perf=perf_dashboard_id)
