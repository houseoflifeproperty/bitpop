#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper script to run layout tests on the buildbots.

Runs the run-webkit-tests script found in third_party/WebKit/Tools/Scripts above
this script. For a complete list of command-line options, pass '--help' on the
command line.

To pass additional options to run-webkit-tests without having them interpreted
as options for this script, include them in an '--options="..."' argument. In
addition, a list of one or more tests or test directories, specified relative
to the main webkit test directory, may be passed on the command line.
"""

import json
import optparse
import os
import re
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def layout_test(options, args):
  """Parse options and call run-webkit-tests, using Python from the tree."""
  build_dir = os.path.abspath(options.build_dir)

  dumprendertree_exe = 'DumpRenderTree.exe'
  if options.driver_name:
    dumprendertree_exe = '%s.exe' % options.driver_name

  # Disable the page heap in case it got left enabled by some previous process.
  try:
    slave_utils.SetPageHeap(build_dir, dumprendertree_exe, False)
  except chromium_utils.PathNotFound:
    # If we don't have gflags.exe, report it but don't worry about it.
    print 'Warning: Couldn\'t disable page heap, if it was already enabled.'

  blink_scripts_dir = chromium_utils.FindUpward(build_dir,
    'third_party', 'WebKit', 'Tools', 'Scripts')
  run_blink_tests = os.path.join(blink_scripts_dir, 'run-webkit-tests')

  slave_name = slave_utils.SlaveBuildName(build_dir)

  command = [run_blink_tests,
             '--no-show-results',
             '--no-new-test-results',
             '--full-results-html',    # For the dashboards.
             '--clobber-old-results',  # Clobber test results before each run.
             '--exit-after-n-failures', '5000',
             '--exit-after-n-crashes-or-timeouts', '100',
            ]

  # TODO(dpranke): we can switch to always using --debug-rwt-logging
  # after all the bots have WebKit r124789 or later.
  capture_obj = slave_utils.RunCommandCaptureFilter()
  slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                         [run_blink_tests, '--help'],
                                         filter_obj=capture_obj)
  if '--debug-rwt-logging' in ''.join(capture_obj.lines):
    command.append('--debug-rwt-logging')
  else:
    command.append('--verbose')

  if options.results_directory:
    # Prior to the fix in https://bugs.webkit.org/show_bug.cgi?id=58272,
    # run_blink_tests expects the results directory to be relative to
    # the configuration directory (e.g., src/webkit/Release). The
    # parameter is given to us relative to build_dir, which is where we
    # will run the command from.
    #
    # When 58272 is landed, run_blink_tests will support absolute file
    # paths as well as paths relative to CWD for non-Chromium ports and
    # paths relative to the configuration dir for Chromium ports. As
    # a transitional fix, we convert to an absolute dir, but once the
    # hack in 58272 is removed, we can use results_dir as-is.
    if not os.path.isabs(options.results_directory):
      if options.results_directory.startswith('../../'):
        options.results_directory = options.results_directory[6:]
      options.results_directory = os.path.abspath(
          os.path.join(os.getcwd(), options.results_directory))
    chromium_utils.RemoveDirectory(options.results_directory)
    command.extend(['--results-directory', options.results_directory])

  if options.target:
    command.extend(['--target', options.target])
  if options.platform:
    command.extend(['--platform', options.platform])

  if options.no_pixel_tests:
    command.append('--no-pixel-tests')
  if options.batch_size:
    command.extend(['--batch-size', options.batch_size])
  if options.run_part:
    command.extend(['--run-part', options.run_part])
  if options.builder_name:
    command.extend(['--builder-name', options.builder_name])
  if options.build_number:
    command.extend(['--build-number', options.build_number])
  command.extend(['--master-name', slave_utils.GetActiveMaster() or ''])
  command.extend(['--build-name', slave_name])
  # On Windows, look for the target in an exact location.
  if sys.platform == 'win32':
    command.extend(['--build-directory', build_dir])
  if options.test_results_server:
    command.extend(['--test-results-server', options.test_results_server])

  if options.enable_pageheap:
    command.append('--time-out-ms=120000')

  if options.time_out_ms:
    command.extend(['--time-out-ms', options.time_out_ms])

  for filename in options.additional_expectations:
    command.append('--additional-expectations=%s' % filename)

  if options.driver_name:
    command.append('--driver-name=%s' % options.driver_name)

  for additional_drt_flag in options.additional_drt_flag:
    command.append('--additional-drt-flag=%s' % additional_drt_flag)

  for test_list in options.test_list:
    command += ['--test-list', test_list]

  if options.enable_leak_detection:
    command.append('--enable-leak-detection')

  # The list of tests is given as arguments.
  command.extend(options.options.split(' '))
  command.extend(args)

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  try:
    if options.enable_pageheap:
      slave_utils.SetPageHeap(build_dir, dumprendertree_exe, True)
    # Run the the tests
    return slave_utils.RunPythonCommandInBuildDir(build_dir, options.target,
                                                  command)
  finally:
    if options.enable_pageheap:
      slave_utils.SetPageHeap(build_dir, dumprendertree_exe, False)

    if options.json_test_results:
      results_dir = options.results_directory
      results_json = os.path.join(results_dir, "failing_results.json")
      with open(results_json, 'rb') as f:
        data = f.read()

      # data is in the form of:
      #   ADD_RESULTS(<json object>);
      # but use a regex match to also support a raw json object.
      m = re.match(r'[^({]*' # From the beginning, take any except '(' or '{'
                  r'(?:'
                    r'\((.*)\);'  # Expect '(<json>);'
                    r'|'          # or
                    r'({.*})'     # '<json object>'
                  r')$',
        data)
      assert m is not None
      data = m.group(1) or m.group(2)

      json_data = json.loads(data)
      assert isinstance(json_data, dict)

      with open(options.json_test_results, 'wb') as f:
        f.write(data)


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('-o', '--results-directory', default='',
                           help='output results directory')
  option_parser.add_option('--build-dir', default='webkit', help='ignored')
  option_parser.add_option('--target', default='',
      help='DumpRenderTree build configuration (Release or Debug)')
  option_parser.add_option('--options', default='',
      help='additional options to pass to run-webkit-tests')
  option_parser.add_option('--platform', default='',
      help=('Platform value passed directly to run_blink_tests.'))
  option_parser.add_option('--no-pixel-tests', action='store_true',
                           default=False,
                           help='disable pixel-to-pixel PNG comparisons')
  option_parser.add_option('--enable-pageheap', action='store_true',
                           default=False, help='Enable page heap checking')
  option_parser.add_option('--batch-size',
                           default=None,
                           help=('Run a the tests in batches (n), after every '
                                 'n tests, the test shell is relaunched.'))
  option_parser.add_option('--run-part',
                           default=None,
                           help=('Run a specified part (n:l), the nth of lth'
                                 ', of the layout tests'))
  option_parser.add_option('--builder-name',
                           default=None,
                           help='The name of the builder running this script.')
  option_parser.add_option('--build-number',
                           default=None,
                           help=('The build number of the builder running'
                                 'this script.'))
  option_parser.add_option('--test-results-server',
                           help=('If specified, upload results json files to '
                                 'this appengine server.'))
  option_parser.add_option('--additional-expectations', action='append',
                           default=[],
                           help=('Path to a test_expectations file '
                                 'that will override previous expectations. '
                                 'Specify multiple times for multiple sets '
                                 'of overrides.'))
  # TODO(dpranke): remove this after we fix the flag in the chromium command.
  option_parser.add_option('--additional-expectations-file',
                           dest='additional_expectations',
                           action='append', default=[],
                           help=('DEPRECATED. '
                                 'Same as --additional-expectations'))
  option_parser.add_option('--time-out-ms',
                           action='store', default=None,
                           help='Set the timeout for each (non-SLOW) test')
  option_parser.add_option('--driver-name',
                           help=('If specified, alternative DumpRenderTree '
                                 'binary to use'))
  option_parser.add_option('--additional-drt-flag', action='append',
                           default=[],
                           help=('If specified, additional command line flag '
                                 'to pass to DumpRenderTree. Specify multiple '
                                 'times to add multiple flags.'))
  option_parser.add_option('--json-test-results',
                           help=('Path to write json results to allow '
                                 'TryJob recipe to know how to ignore '
                                 'expected failures.'))
  option_parser.add_option('--test-list', action='append', metavar='FILE',
                           default=[],
                           help='Read list of tests to run from file.')
  option_parser.add_option('--enable-leak-detection', action='store_true',
                           default=False, help='Enable the leak detection')
  options, args = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  # Disable pageheap checking except on Windows.
  if sys.platform != 'win32':
    options.enable_pageheap = False
  return layout_test(options, args)

if '__main__' == __name__:
  sys.exit(main())
