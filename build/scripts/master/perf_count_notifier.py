# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from twisted.python import log

from buildbot.status.builder import FAILURE, SUCCESS

from master.chromium_notifier import ChromiumNotifier
from master.failures_history import FailuresHistory

# The history of results expire every day.
_EXPIRATION_TIME = 24 * 3600

# Perf results key words used in test result step.
PERF_REGRESS = 'PERF_REGRESS'
PERF_IMPROVE = 'PERF_IMPROVE'
REGRESS = 'REGRESS'
IMPROVE = 'IMPROVE'


class PerfCountNotifier(ChromiumNotifier):
  """This is a status notifier that only alerts on consecutive perf changes.

  The notifier only notifies when a number of consecutive REGRESS or IMPROVE
  perf results are recorded.

  See builder.interfaces.IStatusReceiver for more information about
  parameters type.
  """

  def __init__(self, step_names, minimum_count=5, **kwargs):
    """Initializes the PerfCountNotifier on tests starting with test_name.

    Args:
      step_names: List of perf steps names. This is needed to know perf steps
          from other steps especially when the step is successful.
      minimum_count: The number of minimum consecutive (REGRESS|IMPROVE) needed
          to notify.
    """
    # Set defaults.
    ChromiumNotifier.__init__(self, **kwargs)

    self.minimum_count = minimum_count
    self.step_names = step_names
    self.recent_results = None
    self.new_email_results = None
    self._InitNewEmailResults()
    self._InitRecentResults()
    self.notifications = FailuresHistory(expiration_time=_EXPIRATION_TIME,
                                         size_limit=1000)

  def _InitRecentResults(self):
    """Initializes a new failures history object to store results."""
    self.recent_results = FailuresHistory(expiration_time=_EXPIRATION_TIME,
                                          size_limit=1000)

  def _InitNewEmailResults(self):
    """Initializes a new email results used by each email sent."""
    self.new_email_results = {REGRESS: [], IMPROVE: []}

  def _UpdateResults(self, builder_name, results):
    """Updates the results by adding/removing from the history.

    Args:
      results: List of result tuples, each tuple is of the form
          ('REGRESS|IMPROVE', 'value_name', 'builder').
    """
    new_results_ids = [' '.join(result) for result in results]
    # Delete the old results if the new results do not have them.
    to_delete = [old_id for old_id in self.recent_results.failures
                 if (old_id not in new_results_ids and
                     old_id.endswith(builder_name))]

    for old_id in to_delete:
      self._DeleteResult(old_id)

    # Update the new results history
    for new_id in results:
      self._StoreResult(new_id)

  def _StoreResult(self, result):
    """Stores the result value and removes counter results.

    Example: if this is a REGRESS result then it is stored and its counter
    IMPROVE result, if any, is reset.

    Args:
      result: A tuple of the form ('REGRESS|IMPROVE', 'value_name', 'builder').
    """
    self.recent_results.Put(' '.join(result))
    if result[0] == REGRESS:
      counter_id = IMPROVE + ' '.join(result[1:])
    else:
      counter_id = REGRESS + ' '.join(result[1:])
    # Reset counter_id count since this breaks the consecutive count of it.
    self._DeleteResult(counter_id)

  def _DeleteResult(self, result_id):
    """Removes the history of results identified by result_id.

    Args:
      result_id: The id of the history entry (see _StoreResult() for details).
    """
    num_results = self.recent_results.GetCount(result_id)
    if num_results > 0:
      # This is a hack into FailuresHistory since it does not allow to delete
      # entries in its history unless they are expired.
      # FailuresHistory.failures_count is the total number of entries in the
      # history limitted by FailuresHistory.size_limit.
      del self.recent_results.failures[result_id]
      self.recent_results.failures_count -= num_results

  def _DeleteAllForBuild(self, builder_name):
    """Deletes all results related to a builder."""
    to_delete = [result for result in self.recent_results.failures
                 if result.endswith(builder_name)]
    for result in to_delete:
      self._DeleteResult(result)

  def _IsPerfStep(self, step_status):
    """Checks if the step name is one of the defined perf tests names."""
    return self.getName(step_status) in self.step_names

  def isInterestingStep(self, build_status, step_status, results):
    """Ignore the step if it is not one of the perf results steps.

    Returns:
      True: - if a REGRESS|IMPROVE happens consecutive minimum number of times.
            - if it is not a SUCCESS step and neither REGRESS|IMPROVE.
      False: - if it is a SUCCESS step.
             - if it is a notification which has already been notified.
    """
    if not self._IsPerfStep(step_status):
      return False

    # In case of exceptions, sometimes results output is empty.
    if not results:
      results = [FAILURE]

    builder_name = build_status.getBuilder().getName()
    # If it is a success step, i.e. not interesting, then reset counters.
    if results[0] == SUCCESS:
      self._DeleteAllForBuild(builder_name)
      return False

    # step_text is similar to:
    # media_tests_av_perf <div class="BuildResultInfo"> PERF_REGRESS:
    # time/t (89.07%) PERF_IMPROVE: fps/video (5.40%) </div>
    #
    # regex would return tuples of the form:
    # ('REGRESS', 'time/t', 'linux-rel')
    # ('IMPROVE', 'fps/video', 'win-debug')
    #
    # It is important to put the builder name as the last element in the tuple
    # since it is used to check tests that belong to same builder.
    step_text = ' '.join(step_status.getText())
    log.msg('[PerfCountNotifier] Analyzing failure text: %s.' % step_text)

    perf_regress = perf_improve = ''
    perf_results = []
    if PERF_REGRESS in step_text:
      perf_regress = step_text[step_text.find(PERF_REGRESS) + len(PERF_REGRESS)
                               + 1: step_text.find(PERF_IMPROVE)]
      perf_results.extend([(REGRESS, test_name, builder_name) for test_name in
                           re.findall('(\S+) (?=\(.+\))', perf_regress)])

    if PERF_IMPROVE in step_text:
      # Based on log_parser/process_log.py PerformanceChangesAsText() function,
      # we assume that PERF_REGRESS (if any) appears before PERF_IMPROVE.
      perf_improve = step_text[step_text.find(PERF_IMPROVE) + len(PERF_IMPROVE)
                               + 1:]
      perf_results.extend([(IMPROVE, test_name, builder_name) for test_name in
                           re.findall('(\S+) (?=\(.+\))', perf_improve)])

    # If there is no regress or improve then this could be warning or exception.
    if not perf_results:
      if not self.notifications.GetCount(step_text):
        log.msg('[PerfCountNotifier] Unrecognized step status encountered. '
                'Reporting status as interesting.')
        self.notifications.Put(step_text)
        return True
      else:
        log.msg('[PerfCountNotifier] This problem has already been notified.')
        return False

    is_interesting = False
    update_list = []
    for result in perf_results:
      if len(result) != 3:
        # We expect a tuple similar to ('REGRESS', 'time/t', 'linux-rel')
        continue
      result_id = ' '.join(result)
      update_list.append(result)
      log.msg('[PerfCountNotifier] Result: %s happened %d times in a row.' %
              (result_id, self.recent_results.GetCount(result_id) + 1))
      if self.recent_results.GetCount(result_id) >= self.minimum_count - 1:
        # This is an interesting result! We got the minimum consecutive count of
        # this result, however we still need to check if its been notified.
        if not self.notifications.GetCount(result_id):
          log.msg('[PerfCountNotifier] Result: %s happened enough consecutive '
                  'times to be reported.' % result_id)
          self.notifications.Put(result_id)
          # New results that cause email notifications.
          self.new_email_results[result[0]].append(result[1])
          is_interesting = True
        else:
          log.msg('[PerfCountNotifier] Result: %s has already been notified.' %
                  result_id)

    self._UpdateResults(builder_name, update_list)

    return is_interesting

  def buildMessage(self, builder_name, build_status, results, step_name):
    """Send an email about this interesting step.

    Add the perf regressions/improvements that resulted in this email if any.
    """
    original_header = self.status_header
    msg = ''
    if self.new_email_results[REGRESS]:
      msg += '%s: %s.\n' % (PERF_REGRESS,
                            ', '.join(self.new_email_results[REGRESS]))
    if self.new_email_results[IMPROVE]:
      msg += '%s: %s.\n' % (PERF_IMPROVE,
                            ', '.join(self.new_email_results[IMPROVE]))
    if msg:
      self.status_header += ('\n\nNew perf results in this email:\n%s' % msg)
    email_msg = ChromiumNotifier.buildMessage(self, builder_name, build_status,
                                              results, step_name)
    # Reset header and notification list.
    self.status_header = original_header
    self._InitNewEmailResults()
    return email_msg
