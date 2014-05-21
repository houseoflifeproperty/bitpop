#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the dom perf tests, used by the buildbot slaves.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import logging
import math
import optparse
import os
import sys

from common import chromium_utils
from slave import slave_utils
from slave import xvfb
import simplejson as json

# So we can import google.*_utils below with native Pythons.
sys.path.append(os.path.abspath('src/tools/python'))

USAGE = '%s [options]' % os.path.basename(sys.argv[0])

URL = 'file:///%s/run.html?run=%s%s&reportInJS=1&tags=buildbot_trunk,revision_%s'

TESTS = [
  'Accessors',
  'CloneNodes',
  'CreateNodes',
  'DOMDivWalk',
  'DOMTable',
  'DOMWalk',
  'Events',
  'Get+Elements',
  'GridSort',
  'Template',
]

def geometric_mean(values):
  """Compute a rounded geometric mean from an array of values."""
  if not values:
    return None
  # To avoid infinite value errors, make sure no value is less than 0.001.
  new_values = []
  for value in values:
    if value > 0.001:
      new_values.append(value)
    else:
      new_values.append(0.001)
  # Compute the sum of the log of the values.
  log_sum = sum(map(math.log, new_values))
  # Raise e to that sum over the number of values.
  mean = math.pow(math.e, (log_sum / len(new_values)))
  # Return the rounded mean.
  return int(round(mean))

def print_result(top, name, score_string, refbuild):
  prefix = ''
  if top:
    prefix = '*'
  score = int(round(float(score_string)))
  score_label = 'score'
  if refbuild:
    score_label = 'score_ref'
  print ('%sRESULT %s: %s= %d score (bigger is better)' %
         (prefix, name, score_label, score))


def dom_perf(options, args):
  """Using the target build configuration, run the dom perf test."""

  build_dir = os.path.abspath(options.build_dir)
  if chromium_utils.IsWindows():
    test_exe_name = 'performance_ui_tests.exe'
  else:
    test_exe_name = 'performance_ui_tests'

  if chromium_utils.IsMac():
    is_make_or_ninja = (options.factory_properties.get("gclient_env", {})
        .get('GYP_GENERATORS', '') in ('ninja', 'make'))
    if is_make_or_ninja:
      build_dir = os.path.join(os.path.dirname(build_dir), 'out')
    else:
      build_dir = os.path.join(os.path.dirname(build_dir), 'xcodebuild')
  elif chromium_utils.IsLinux():
    build_dir = os.path.join(os.path.dirname(build_dir), 'sconsbuild')
  test_exe_path = os.path.join(build_dir, options.target, test_exe_name)
  if not os.path.exists(test_exe_path):
    raise chromium_utils.PathNotFound('Unable to find %s' % test_exe_path)

  # Find the current revision to pass to the test.
  build_revision = slave_utils.SubversionRevision(build_dir)

  # Compute the path to the test data.
  src_dir = os.path.dirname(build_dir)
  data_dir = os.path.join(src_dir, 'data')
  dom_perf_dir = os.path.join(data_dir, 'dom_perf')

  iterations = ''  # Default
  if options.target == 'Debug':
    iterations = '&minIterations=1'

  def run_and_print(use_refbuild):
    # Windows used to write to the root of C:, but that doesn't work
    # on Vista so we write into the build folder instead.
    suffix = ''
    if (use_refbuild):
      suffix = '_ref'
    output_file = os.path.join(build_dir, options.target,
                               'dom_perf_result_%s%s.txt' % (build_revision,
                                                             suffix))

    result = 0
    compiled_data = []
    for test in TESTS:
      url = URL % (dom_perf_dir, test, iterations, build_revision)
      url_flag = '--url=%s' % url

      command = [test_exe_path,
                 '--wait_cookie_name=__domperf_finished',
                 '--jsvar=__domperf_result',
                 '--jsvar_output=%s' % output_file,
                 '--gtest_filter=UrlFetchTest.UrlFetch',
                 url_flag]
      if use_refbuild:
        command.append('--reference_build')

      print "Executing: "
      print command
      result |= chromium_utils.RunCommand(command)

      # Open the resulting file and display it.
      data = json.load(open(output_file, 'r'))
      for suite in data['BenchmarkSuites']:
        # Skip benchmarks that we didn't actually run this time around.
        if len(suite['Benchmarks']) == 0 and suite['score'] == 0:
          continue
        compiled_data.append(suite)

    # Now give the geometric mean as the total for the combined runs.
    total = geometric_mean([s['score'] for s in compiled_data])
    print_result(True, 'Total', total, use_refbuild)
    for suite in compiled_data:
      print_result(False, suite['name'], suite['score'], use_refbuild)

    return result

  try:
    if chromium_utils.IsLinux():
      xvfb.StartVirtualX(options.target,
                         os.path.join(build_dir, options.target))

    result = run_and_print(False)
    result |= run_and_print(True)

  finally:
    if chromium_utils.IsLinux():
      xvfb.StopVirtualX(options.target)

  return result


def main():
  # Initialize logging.
  log_level = logging.INFO
  logging.basicConfig(level=log_level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  option_parser = optparse.OptionParser(usage=USAGE)

  option_parser.add_option('', '--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  chromium_utils.AddPropertiesOptions(option_parser)
  options, args = option_parser.parse_args()
  return dom_perf(options, args)

if '__main__' == __name__:
  sys.exit(main())
