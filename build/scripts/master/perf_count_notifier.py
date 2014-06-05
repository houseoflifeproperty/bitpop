# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import time
from urllib import urlencode
from urlparse import parse_qs, urlsplit, urlunsplit

from buildbot.status.builder import FAILURE, SUCCESS
from master import build_utils
from master.chromium_notifier import ChromiumNotifier
from master.failures_history import FailuresHistory

from twisted.internet import defer
from twisted.python import log

try:
  # Create a block to work around evil sys.modules manipulation in
  # email/__init__.py that triggers pylint false positives.
  # pylint has issues importing it.
  # pylint: disable=E0611,F0401
  from email.MIMEMultipart import MIMEMultipart
  from email.MIMEText import MIMEText
  from email.Utils import formatdate
except ImportError:
  raise

# The history of results expire every day.
_EXPIRATION_TIME = 24 * 3600

# Perf results key words used in test result step.
PERF_REGRESS = 'PERF_REGRESS'
PERF_IMPROVE = 'PERF_IMPROVE'
REGRESS = 'REGRESS'
IMPROVE = 'IMPROVE'
# Key to last time an email is sent per builder
EMAIL_TIME = 'EMAIL_TIME'
GRAPH_URL = 'GRAPH_URL'

def PerfLog(msg):
  log.msg('[PerfCountNotifier] %s' % msg)


class PerfCountNotifier(ChromiumNotifier):
  """This is a status notifier that only alerts on consecutive perf changes.

  The notifier only notifies when a number of consecutive REGRESS or IMPROVE
  perf results are recorded.

  See builder.interfaces.IStatusReceiver for more information about
  parameters type.
  """

  def __init__(self, step_names, minimum_count=5, combine_results=True,
               **kwargs):
    """Initializes the PerfCountNotifier on tests starting with test_name.

    Args:
      step_names: List of perf steps names. This is needed to know perf steps
          from other steps especially when the step is successful.
      minimum_count: The number of minimum consecutive (REGRESS|IMPROVE) needed
          to notify.
      combine_results: Combine summary results email for all builders in one.
    """
    # Set defaults.
    ChromiumNotifier.__init__(self, **kwargs)

    self.minimum_count = minimum_count
    self.combine_results = combine_results
    self.step_names = step_names
    self.recent_results = None
    self.error_email = False
    self.new_email_results = {}
    self.recent_results = FailuresHistory(expiration_time=_EXPIRATION_TIME,
                                          size_limit=1000)

  def AddNewEmailResult(self, result):
    """Stores an email result for a builder.

    Args:
      result: A tuple of the form ('REGRESS|IMPROVE', 'value_name', 'builder').
    """
    builder_name = result[2]
    build_results = self.GetEmailResults(builder_name)
    if not result[1] in build_results[result[0]]:
      build_results[result[0]].append(result[1])
    else:
      PerfLog('(%s) email result has already been stored.' % ', '.join(result))

  def GetEmailResults(self, builder_name):
    """Returns the email results for a builder."""
    if not builder_name in self.new_email_results:
      self.new_email_results[builder_name] = GetNewBuilderResult()
    return self.new_email_results[builder_name]

  def _UpdateResults(self, builder_name, results):
    """Updates the results by adding/removing from the history.

    Args:
      builder_name: Builder name the results belong to.
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
    """Deletes all test results related to a builder."""
    to_delete = [result for result in self.recent_results.failures
                 if result.endswith(builder_name)]
    for result in to_delete:
      self._DeleteResult(result)

  def _ResetResults(self, builder_name):
    """Reset pending email results for builder."""
    builders = [builder_name]
    if self.combine_results:
      builders = self.new_email_results.keys()
    for builder_name in builders:
      self._DeleteAllForBuild(builder_name)
      self.new_email_results[builder_name] = GetNewBuilderResult()
      self.new_email_results[builder_name][EMAIL_TIME] = time.time()

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
    self.error_email = False
    step_text = ' '.join(step_status.getText())
    PerfLog('Analyzing failure text: %s.' % step_text)
    if (not self._IsPerfStep(step_status) or
        not self.isInterestingBuilder(build_status.getBuilder())):
      return False

    # In case of exceptions, sometimes results output is empty.
    if not results:
      results = [FAILURE]
    builder_name = build_status.getBuilder().getName()
    self.SetBuilderGraphURL(self.getName(step_status), build_status)
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
    PerfLog('Analyzing failure text: %s.' % step_text)

    perf_regress = perf_improve = ''
    perf_results = []
    if PERF_REGRESS in step_text:
      perf_regress = step_text[step_text.find(PERF_REGRESS) + len(PERF_REGRESS)
                               + 1: step_text.find(PERF_IMPROVE)]
      perf_results.extend([(REGRESS, test_name, builder_name) for test_name in
                           re.findall(r'(\S+) (?=\(.+\))', perf_regress)])

    if PERF_IMPROVE in step_text:
      # Based on log_parser/process_log.py PerformanceChangesAsText() function,
      # we assume that PERF_REGRESS (if any) appears before PERF_IMPROVE.
      perf_improve = step_text[step_text.find(PERF_IMPROVE) + len(PERF_IMPROVE)
                               + 1:]
      perf_results.extend([(IMPROVE, test_name, builder_name) for test_name in
                           re.findall(r'(\S+) (?=\(.+\))', perf_improve)])

    # If there is no regress or improve then this could be warning or exception.
    if not perf_results:
      if not self.recent_results.GetCount(step_text):
        PerfLog('Unrecognized step status. Reporting status as interesting.')
        # Force the build box to show in email
        self.error_email = True
        self.recent_results.Put(step_text)
        return True
      else:
        PerfLog('This problem has already been notified.')
        return False

    update_list = []
    for result in perf_results:
      if len(result) != 3:
        # We expect a tuple similar to ('REGRESS', 'time/t', 'linux-rel')
        continue
      result_id = ' '.join(result)
      update_list.append(result)
      PerfLog('Result: %s happened %d times in a row.' %
              (result_id, self.recent_results.GetCount(result_id) + 1))
      if self.recent_results.GetCount(result_id) >= self.minimum_count - 1:
        # This is an interesting result! We got the minimum consecutive count of
        # this result.  Store it in email results.
        PerfLog('Result: %s happened enough consecutive times to be reported.'
                % result_id)
        self.AddNewEmailResult(result)

    self._UpdateResults(builder_name, update_list)
    # Final decision is made based on whether there are any notifications to
    # email based on this and older build results.
    return self.ShouldSendEmail(builder_name)

  def buildMessage(self, builder_name, build_status, results, step_name):
    """Send an email about this interesting step.

    Add the perf regressions/improvements that resulted in this email if any.
    """
    PerfLog('About to send an email.')
    email_subject = self.GetEmailSubject(builder_name, build_status, results,
                                         step_name)
    email_body = self.GetEmailBody(builder_name, build_status, results,
                                   step_name)
    html_content = (
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>%s</body></html>' %
        email_body)
    defered_object = self.BuildEmailObject(email_subject, html_content,
                                           builder_name, build_status,
                                           step_name)
    self._ResetResults(builder_name)
    return defered_object

  def ShouldSendEmail(self, builder_name):
    """Returns if we should send a summary email at this moment.

    Returns:
        True if it has been at least minimum_delay_between_alert since the
        last email sent. False otherwise.
    """
    builders = [builder_name]
    if self.combine_results:
      builders = self.new_email_results.keys()
    for builder_name in builders:
      if self._ShouldSendEmail(builder_name):
        return True
    return False

  def _ShouldSendEmail(self, builder_name):
    results = self.GetEmailResults(builder_name)
    last_time_mail_sent = results[EMAIL_TIME]
    if (last_time_mail_sent and last_time_mail_sent >
        time.time() - self.minimum_delay_between_alert):
      # Rate limit tree alerts.
      PerfLog('Time since last email is too short. Should not send email.')
      return False
    # Return True if there are any builder results to email about.
    return results and (results[REGRESS] or results[IMPROVE])

  def GetEmailSubject(self, builder_name, build_status, results, step_name):
    """Returns the subject of for an email based on perf results."""
    project_name = self.master_status.getTitle()
    latest_revision = build_utils.getLatestRevision(build_status)
    result = 'changes'
    builders = [builder_name]
    if self.combine_results:
      builders = self.new_email_results.keys()
    return ('%s %s on %s, revision %s' %
            (project_name, result, ', '.join(builders), str(latest_revision)))

  def GetEmailHeader(self, builder_name, build_status, results, step_name):
    """Returns a header message in an email.

    Used for backward compatibility with chromium_notifier.  It allows the
    users to add text to every email from the master.cfg setup.
    """
    status_text = self.status_header % {
        'builder': builder_name,
        'steps': step_name,
        'results': results
    }
    return status_text

  def GetEmailBody(self, builder_name, build_status, results, step_name):
    """Returns the main email body content."""
    email_body = ''
    builders = [builder_name]
    if self.combine_results:
      builders = self.new_email_results.keys()
    for builder_name in builders:
      email_body += '%s%s\n' % (
          self.GetEmailHeader(builder_name, build_status, results, step_name),
          self.GetPerfEmailBody(builder_name)
          )
    # Latest build box is not relevant with multiple builder results combined.
    if not self.combine_results or self.error_email:
      email_body += ('\n\nLatest build results:%s' %
                     self.GenStepBox(builder_name, build_status, step_name))
    PerfLog('Perf email body: %s' % email_body)
    return email_body.replace('\n', '<br>')

  def GetPerfEmailBody(self, builder_name):
    builder_results = self.GetEmailResults(builder_name)
    graph_url = builder_results[GRAPH_URL]
    msg = ''
    # Add regression HTML links.
    if builder_results[REGRESS]:
      test_urls = CreateHTMLTestURLList(graph_url, builder_results[REGRESS])
      msg += '<strong>%s</strong>: %s.\n' % (PERF_REGRESS, ', '.join(test_urls))
    # Add improvement HTML links.
    if builder_results[IMPROVE]:
      test_urls = CreateHTMLTestURLList(graph_url,
                                        builder_results[IMPROVE])
      msg += '<strong>%s</strong>: %s.\n' % (PERF_IMPROVE, ', '.join(test_urls))
    return msg or 'No perf results.\n'

  def BuildEmailObject(self, email_subject, html_content, builder_name,
                       build_status, step_name):
    """Creates an email object ready to be sent."""
    m = MIMEMultipart('alternative')
    m.attach(MIMEText(html_content, 'html', 'iso-8859-1'))
    m['Date'] = formatdate(localtime=True)
    m['Subject'] = email_subject
    m['From'] = self.fromaddr
    if self.reply_to:
      m['Reply-To'] = self.reply_to
    recipients = list(self.extraRecipients[:])
    dl = []
    if self.sendToInterestedUsers and self.lookup:
      for u in build_status.getInterestedUsers():
        d = defer.maybeDeferred(self.lookup.getAddress, u)
        d.addCallback(recipients.append)
        dl.append(d)
    defered_object = defer.DeferredList(dl)
    defered_object.addCallback(self._gotRecipients, recipients, m)
    defered_object.addCallback(self.getFinishedMessage, builder_name,
                               build_status, step_name)
    return defered_object

  def GenStepBox(self, builder_name, build_status, step_name):
    """Generates a HTML styled summary box for one step."""
    waterfall_url = self.master_status.getBuildbotURL()
    styles = dict(build_utils.DEFAULT_STYLES)
    builder_results = self.GetEmailResults(builder_name)
    if builder_results[IMPROVE] and not builder_results[REGRESS]:
      styles['warnings'] = styles['success']
    return build_utils.EmailableBuildTable_bb8(build_status, waterfall_url,
                                               styles=styles,
                                               step_names=[step_name])

  def SetBuilderGraphURL(self, step_name, build_status):
    """Stores the graph URL used in emails for this builder."""
    builder_name = build_status.getBuilder().getName()
    builder_results = self.GetEmailResults(builder_name)
    graph_url = GetGraphURL(step_name, build_status)
    latest_revision = build_utils.getLatestRevision(build_status)
    if latest_revision:
      graph_url = SetQueryParameter(graph_url, 'rev', latest_revision)
    builder_results[GRAPH_URL] = graph_url


def GetStepByName(build_status, step_name):
  """Returns the build step with step_name."""
  for step in build_status.getSteps():
    if step.getName() == step_name:
      return step
  return None


def GetGraphURL(step_name, build_status):
  """Returns the graph result's URL from the step with step_name.

  Args:
    step_name: The name of the step to get the URL from.
    build_status: The build status containing all steps in this build.
  Return:
    A string URL for the results graph page in the status step.
  """
  step = GetStepByName(build_status, step_name)
  if step and step.getURLs():
    # Find the URL for results page
    for name, target in step.getURLs().iteritems():
      if 'report.html' in target:
        PerfLog('Found graph URL %s %s ' % (name, target))
        return SetQueryParameter(target, 'history', 150)
  PerfLog('Could not find graph URL, step_name: %s.' % step_name)
  return None


def CreateHTMLTestURLList(graph_url, test_names):
  """Creates a list of href HTML graph links for each test name result.

  Args:
    graph_url: The main result page URL.
    test_names: A list of test names that should be included in the email.
  Return:
    A list of strings, each containing HTML href links to specific test
    results with graph and trace parameters set.  Example:
    graph_url = 'http://build.chromium.org/f/chromium/perf/linux-release/\
                 media_tests_av_perf/report.html?history=150'
    test_name = ['audio_latency/latency']
    Return value = ['<a href="http://build.chromium.org/f/chromium/perf/\
        linux-release/media_tests_av_perf/report.html?history=150&\
        graph=audio_latency&trace=latency">audio_latency/latency</a>']
  """

  def CreateTraceURL(test_name):
    names = test_name.split('/')
    url = SetQueryParameter(graph_url, 'graph', names[0])
    if len(names) > 1:
      url = SetQueryParameter(url, 'trace', names[1], append_param=True)
    return url

  urls = []
  for name in test_names:
    urls.append('<a href="%s">%s</a>' % (CreateTraceURL(name), name))
  return urls


def GetNewBuilderResult():
  return {
      REGRESS: [],
      IMPROVE: [],
      EMAIL_TIME: None,
      GRAPH_URL: ''
      }


def SetQueryParameter(url, param_name, param_value, append_param=False):
  """Returns a url with the parameter value pair updated or added.

  If append_param=True then the URL will append a new param value to the URL.
  """
  if not url:
    return '%s=%s' % (param_name, param_value)
  scheme, netloc, path, query_string, fragment = urlsplit(url)
  query_params = parse_qs(query_string)
  if append_param and param_name in query_params:
    query_params[param_name].append(param_value)
  else:
    query_params[param_name] = [param_value]
  new_query_string = urlencode(query_params, doseq=True)
  return urlunsplit((scheme, netloc, path, new_query_string, fragment))
