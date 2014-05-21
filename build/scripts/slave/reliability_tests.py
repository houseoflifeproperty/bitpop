#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to retrieve reliability test results.

This script queries the ChromeBot test dashboard to get the reliability test
results for a given build. It returns 0 if no new crashes have been reported.

For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import re
import simplejson
import sys
import time
import urllib2

from slave import slave_utils

# Method could be a function
# pylint: disable=R0201

# Return codes for the staging step.  The difference between warning and
# failure is that the reliability tests will still work in case of a warning,
# but may have some issues (such as no symbols).  In the case of a failure,
# the tests won't work at all.
(STAGE_SUCCESS, STAGE_WARNING, STAGE_FAILURE) = range(3)

# Max number of crash causes to print in the output for a given result set.
CRASH_CAUSE_PRINT_LIMIT = 50

# Default file name to find known crashes.
KNOWN_CRASHES_FILE_NAME = 'known_crashes.txt'

# Types of known crashes.
(PREFIX, SUBSTRING, REGEX) = range(3)

HOWTO_LINK = ('http://sites.google.com/a/chromium.org/dev/developers'
              '/how-tos/reliability-tests')

CHROMEBOT_DASHBOARD = 'http://localhost/chromebot'


class KnownCrash(object):
  """Representation of a known crash.

  Contains the known crash's signature pattern as well as its type, which
  indicates how the crash should be matched against a crash signature.
  """
  TYPES = {'PREFIX': PREFIX,
           'SUBSTRING': SUBSTRING,
           'REGEX': REGEX}

  def __init__(self, line, line_location=''):
    """Construct a known crash object from a line in the known crashes file.

    Parses the line, storing the relevant fields inside the newly created
    object.

    Args:
      line: The line from the known crashes file.
      line_location: Optional, debugging information used in the error output of
        invalid pattern lines.  Should contain information relevant to the line
        (e.g. file name and line number).
    """
    self.__valid = False
    self.__type = None
    self.__type_string = ''
    self.__pattern = None
    self._ParseLine(line, line_location)

  def __eq__(self, other):
    if not isinstance(other, KnownCrash):
      return False
    if self.__valid != other.IsValid():
      return False
    if self.__type != other.GetType():
      return False
    if self.__pattern != other.GetPattern():
      return False
    return True

  def __ne__(self, other):
    return not self.__eq__(other)

  def __cmp__(self, other):
    if not isinstance(other, KnownCrash):
      return -1
    # First compare by type.
    type_cmp = cmp(self.__type, other.GetType())
    if type_cmp != 0:
      return type_cmp
    # Second, compare by signature pattern.
    return cmp(self.__pattern, other.GetPattern())

  def __repr__(self):
    return ('valid: %s, type: %s, pattern: %s' %
            (self.__valid, self.__type_string, self.__pattern))

  def IsValid(self):
    return self.__valid

  def GetType(self):
    return self.__type

  def GetTypeAsString(self):
    return self.__type_string

  def GetPattern(self):
    return self.__pattern

  def Match(self, signature):
    """Determine if a given signature matches the pattern of this known crash.

    Args:
      signature: The signature of the crash to match.
    Returns:
      True if the signature matches this known crash.
    """
    if not self.__valid:
      return False

    if self.__type == REGEX:
      # This is a pattern in regular expression syntax.
      crash_pattern = re.compile(self.__pattern)
      return bool(crash_pattern.search(signature))

    if self.__type == SUBSTRING:
      # This is a signature substring.  Matching is case-insensitive.
      return signature.lower().find(self.__pattern) != -1

    # This is a signature prefix.  Matching is case-insensitive.
    return signature.lower().startswith(self.__pattern)

  def _FormatPattern(self, pattern_type, pattern):
    """Format the given pattern as appropriate for its type."""
    if pattern_type in (PREFIX, SUBSTRING):
      # Prefix and substring patterns are case-insensitive.
      pattern = pattern.lower()
    return pattern

  def _ParseLine(self, line, line_location):
    """Parse a known crashes line and store the results in this object."""
    line = line.strip()
    if not line or line.startswith('#'):
      return  # Return early (don't mark as valid)

    if line.find(':') == -1:
      sys.stderr.write('%sInvalid pattern line: %s\n' % (line_location, line))
      return  # Return early (don't mark as valid)

    line_type, pattern = line.split(':', 1)
    line_type = line_type.strip().upper()
    if line_type not in self.TYPES:
      sys.stderr.write('%sInvalid pattern line: %s\n' % (line_location, line))
      return  # Return early (don't mark as valid)

    pattern = pattern.strip()
    if not pattern:
      sys.stderr.write('%sInvalid pattern line: %s\n' % (line_location, line))
      return  # Return early (don't mark as valid)

    self.__type = self.TYPES[line_type]
    self.__type_string = line_type
    self.__pattern = self._FormatPattern(self.__type, pattern)
    self.__valid = True


class CrashCause(object):
  """Representation of the cause of crash."""

  def __init__(self, key):
    """Construct a CrashCause object.

    Args:
      type: type of test seeing this crash, either URL_TEST or UI_TEST.
      key: either URLs or UI sequences that can repro the crash.
    """
    self.__key = key

  def GetKey(self):
    return self.__key

  def Print(self):
    print 'Unfiltered URL: %s' % self.GetKey()


class CrashReport(object):
  """Representation of crash report(s) that have same stack trace.

  Contains the information of crash reports with same stack trace. The
  information includes list of URLs or UI sequences that can repro the crash
  as well as the stack trace.
  """

  def __init__(self, causes, stack):
    """Construct a CrashReport object.

    Args:
      causes: list of CrashCause objects that can repro the crash.
      stack: the crash stack trace which is a list of strings, representing
      functions in crash stack.
    """
    self.__causes = causes
    self.__stack = stack

  def GetCauses(self):
    return self.__causes

  def GetStack(self):
    return self.__stack

  def GetCrashSignature(self, total_num_func=0):
    """Get crash signature based on stack trace in crash report.

    Args:
      total_num_func: the total number of functions used to construct the
                      signature. If 0, then all present functions in stack
                      trace are used.
    Returns:
      The signature of stack trace, which is the concatenation of top N,
      specified by total_num_func, functions in chrome.dll on the crash stack.
    """
    num_func = 0
    functions = []
    for stack_line in self.GetStack():
      stack_line = stack_line.lower()
      if stack_line.startswith('chrome'):
        function_start = stack_line.find('!')
        function_end = stack_line.find('+0x')
        if function_end == -1:
          function_end = stack_line.find(' [')
        if num_func > 0:
          functions.append('___')
        functions.append(stack_line[function_start+1:function_end])
        num_func += 1
        if total_num_func > 0 and num_func >= total_num_func:
          break
    return ''.join(functions)

  def HasUsefulTrace(self):
    """Return False if the stack has no useful debugging information."""
    if len(self.__stack) < 2:
      return False
    first_frame = self.__stack[0]
    if first_frame.startswith('WARNING'):
      first_frame = self.__stack[1]
    # If the first frame of the stack is inside Flash, it is not useful.
    if first_frame.startswith('NPSWF32'):
      return False
    # Return false for crash inside windows media player plug-in.
    if first_frame.startswith('npdsplay'):
      return False
    # Return false for a stack loaded with incorrect symbols.
    for frame in self.__stack:
      if frame.find('RelaunchChromeBrowserWithNewCommandLineIfNeeded') > 0:
        return False
    return True

  def Join(self, crash):
    """Aggregating two crash reports with same stack traces by combining their
    list of causes.
    """
    if self.GetCrashSignature() == crash.GetCrashSignature():
      self.GetCauses().extend(crash.GetCauses())

  def Print(self):
    """Print out the information on the crash report(s)."""
    print 'Repro information:'
    i = 0
    for cause in self.GetCauses():
      if i < CRASH_CAUSE_PRINT_LIMIT:
        cause.Print()
        i += 1
      elif i == CRASH_CAUSE_PRINT_LIMIT:
        print '...and more'
        break
    print '\nStack trace:'
    for line in self.GetStack():
      print line
    print ''


def PrintCrashes(crashes):
  """Print out the list of crash reports."""
  if not crashes:
    return
  for crash in crashes:
    print '-' * 20
    crash.Print()
  print '-' * 20


def FindMatchingKnownCrash(signature, known_crashes):
  """Find a matching crash in the list of known crashes for a given signature.

  Returns the first matching crash in the known crashes list.

  Args:
    signature: the given crash signature.
    known_crashes: the list of known crashes.

  Returns:
    The first matching known crash found in the list.
  """
  for known_crash in known_crashes:
    if known_crash.Match(signature):
      return known_crash
  return None


def FindNewCrashes(crashes, known_crashes):
  """Find new crash reports that are not in known list.

  Args:
    crashes: a list of crash reports.
    known_crashes: a list of known crashes.
  Returns:
    A list of crash reports whose stack traces are not in the known list.
    In addition, if multiple input crash reports have same stack trace, they
    are aggregated, i.e. one crash report with aggregated repro infomation is
    returned.
  """
  new_crashes = []
  for crash in crashes:
    if not crash.HasUsefulTrace():
      continue
    crash_signature = crash.GetCrashSignature()
    if not crash_signature:
      continue
    known_crash = FindMatchingKnownCrash(crash_signature, known_crashes)
    if known_crash:
      print 'INFO: known stack trace signature found.'
      print '(match %s, %s)\n' % (known_crash.GetTypeAsString(),
                                  known_crash.GetPattern())
    else:
      aggregate = False
      for new_crash in new_crashes:
        if crash_signature == new_crash.GetCrashSignature():
          aggregate = True
          new_crash.Join(crash)
          break
      if aggregate:
        continue
      print 'INFO: NEW stack trace signature found:'
      print crash_signature
      print ''
      new_crashes.append(crash)
  return new_crashes


def FindUnmatchedCrashes(crashes, known_crashes):
  """Find crashes in the known list that don't have matching crashes.

  Args:
    crashes: a list of crash reports.
    known_crashes: a list of known crashes.
  Returns:
    A list of known crashes without matching crashes.
  """
  # Make a copy to not modify the caller's copy.
  unmatched_known_crashes = list(known_crashes)
  found_crash_signatures = []
  for crash in crashes:
    crash_signature = crash.GetCrashSignature()
    if not crash_signature:
      continue
    if crash_signature in found_crash_signatures:
      continue
    found_crash_signatures.append(crash_signature)
    while True:
      matching_crash = FindMatchingKnownCrash(crash_signature,
                                              unmatched_known_crashes)
      if not matching_crash:
        break
      unmatched_known_crashes.remove(matching_crash)
  unmatched_known_crashes.sort()
  return unmatched_known_crashes


def GetKnownCrashes(data_dir):
  """Find the file containing known crashes and get known crash patterns.

  Args:
    data_dir: The path to the reliability data directory.
        If empty, use this script's directory.
  Yields:
    The list of known crashes.
  """
  if data_dir:
    data_dir = os.path.abspath(data_dir)
  else:
    data_dir = os.path.dirname(sys.argv[0])

  filename = os.path.join(data_dir, KNOWN_CRASHES_FILE_NAME)

  known_crashes = ''

  try:
    f_known_crashes = open(filename)
    known_crashes = f_known_crashes.read()
    f_known_crashes.close()
  except IOError:
    sys.stderr.write('INFO: Cannot find %s\n' % KNOWN_CRASHES_FILE_NAME)

  lines = known_crashes.splitlines()
  for i in xrange(len(lines)):
    line_location = '%s:%d: ' % (KNOWN_CRASHES_FILE_NAME, i + 1)
    known_crash = KnownCrash(lines[i], line_location)
    if known_crash.IsValid():
      yield known_crash


def DisplayRevisionRange(last_revision, prev_revision):
  """Display the link to see the changes in this build."""
  # Use prev_revision.chromium_rev + 1 because the SVN changelog is inclusive.
  # The build for prev_revision should have already been tested.
  prev_chromium_rev = int(prev_revision.chromium_rev) + 1
  print 'Changes since last run of reliability test:'
  print ('http://build.chromium.org/buildbot/perf/'
         'dashboard/ui/changelog.html?url=/trunk/src&mode=html'
         '&range=%s:%s' % (prev_chromium_rev, last_revision.chromium_rev))


def QueryReliabilityResults(build_type, platform, build_id):
  """Query test results for a given reliability test run.

  Args:
    test_id: the ID of the test run.

  Returns:
    The total number of results, the total number of crashes, and a list of
    crash reports.
  """
  raw_data = ''
  results_url = ('%s/?action=buildsummary&format=json&build_type=%s'
                 '&platform=%s&build_id=%s' %
                 (CHROMEBOT_DASHBOARD, build_type, platform, build_id))
  for _ in xrange(3):
    try:
      response = urllib2.urlopen(results_url)
      raw_data = response.read()
      break
    except urllib2.URLError:
      print 'Failed to read from URL: ' + results_url
      time.sleep(2)
  if not raw_data:
    print 'Cannot read reliability data'
    return (0, 0, [])

  num_success = 0
  num_error = 0
  num_crash = 0
  num_crash_dump = 0
  num_timeout = 0
  crashes = []
  print results_url
  data = simplejson.loads(raw_data)
  if data:
    if 'success_count' in data:
      num_success = int(data['success_count'])
    if 'error_count' in data:
      num_error = int(data['error_count'])
    if 'crash_count' in data:
      num_crash = int(data['crash_count'])
    if 'uploaded_crash_count' in data:
      num_crash_dump = int(data['uploaded_crash_count'])
    if 'timeout_count' in data:
      num_timeout = int(data['timeout_count'])
    if 'failures' in data:
      for result in data['failures']:
        stack_trace = []
        if result['stack_trace']:
          stack_trace = result['stack_trace'].splitlines()
        crashes.append(CrashReport([CrashCause(result['url'])], stack_trace))
  else:
    print 'Cannot parse reliability data.'

  print ('success: %s; crashes: %s; crash dumps: %s; timeout: %s' %
         (num_success, num_crash, num_crash_dump, num_timeout))

  dashboard_url = ('%s/?action=buildsummary&build_type=%s&platform=%s'
                   '&build_id=%s' %
                   (CHROMEBOT_DASHBOARD, build_type, platform, build_id))

  print 'Detailed report: %s' % dashboard_url

  total_url_visited = num_success + num_error + num_crash + num_timeout
  return (total_url_visited, num_crash, crashes)


def reliability_tests(options):
  platform = options.platform.lower()
  build_id = options.build_id
  build_type = options.build_type

  print '\nResults for extended list of web sites:'
  total, crash_num, crashes = QueryReliabilityResults(build_type, platform,
                                                      build_id)

  print '\nChecking new crashes...'
  known_crashes = list(GetKnownCrashes(options.data_dir))
  new_crashes = FindNewCrashes(crashes, known_crashes)

  regression = False
  if new_crashes:
    # Regression if new crash signature found.
    print '\nREGRESSION: NEW crash stack traces found.'
    PrintCrashes(new_crashes)
    regression = True
  elif crash_num * 3000 > total:
    # Even if no new crash signature was found, we still report a regression
    # if there is a significant increase on crash rate. We do this because
    # some crashes may not have valid dumps. Report regression if the crash
    # rate is greater than 0.33 per thousand for extended urls (>50k).
    print '\nREGRESSION: Significant increase on crash rate.'
    regression = True
  elif total == 0:
    print '\nRELIABILITY TEST FAILURE: No results found.'
    return slave_utils.WARNING_EXIT_CODE
  else:
    print '\nSuccess'

  if regression:
    print '\nACTION NEEDED: see %s to fix regressions.' % HOWTO_LINK
    return slave_utils.ERROR_EXIT_CODE

  return 0


def main():
  parser = optparse.OptionParser()
  parser.add_option('', '--test-run', action='store_true',
                    default=False,
                    help='test run. For things like staging and sleep, print'
                          'a message instead of doing the actual work')
  VALID_PLATFORMS = ('win', 'mac', 'linux', 'linux64')
  parser.add_option('', '--platform', type='choice', default='win',
                    choices=VALID_PLATFORMS,
                    help='Platform of the results to query, valid values: ' +
                         ' '.join(VALID_PLATFORMS))
  parser.add_option('', '--build-id', type='string', default='',
                    help='Specify the build number.')
  VALID_BUILD_TYPE = ('chromium', 'official')
  parser.add_option('', '--build-type', type='choice', default='chromium',
                    choices=VALID_BUILD_TYPE,
                    help='Either official or chromium.')
  parser.add_option('', '--data-dir', type='string', default='',
                    help='path to the directory containing the reliability '
                         'data, such as the known crashes, use the script '
                         'directory if not specified')

  options, args = parser.parse_args()
  if args:
    parser.error('Args not supported.')
  return reliability_tests(options)


if '__main__' == __name__:
  sys.exit(main())
