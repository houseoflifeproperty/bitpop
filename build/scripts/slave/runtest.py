#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run a chrome test executable, used by the buildbot slaves.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import copy
import logging
import optparse
import os
import re
import stat
import sys
import tempfile

# sys.path needs to be modified here because python2.6 automatically adds the
# system "google" module (/usr/lib/pymodules/python2.6/google) to sys.modules
# when we import "chromium_config" (I don't know why it does this). This causes
# the import of our local "google.*" modules to fail because python seems to
# only look for a system "google.*", even if our path is in sys.path before
# importing "google.*". If we modify sys.path here, before importing
# "chromium_config", python2.6 properly uses our path to find our "google.*"
# (even though it still automatically adds the system "google" module to
# sys.modules, and probably should still be using that to resolve "google.*",
# which I really don't understand).
sys.path.insert(0, os.path.abspath('src/tools/python'))

# Because of this dependency on a chromium checkout, we need to disable some
# pylint checks.
# pylint: disable=E0611
# pylint: disable=E1101
from common import chromium_utils
from common import gtest_utils
import config
from slave import crash_utils
from slave import gtest_slave_utils
from slave import process_log_utils
from slave import slave_utils
from slave import xvfb
from slave.gtest.json_results_generator import GetSvnRevision

USAGE = '%s [options] test.exe [test args]' % os.path.basename(sys.argv[0])

CHROME_SANDBOX_PATH = '/opt/chromium/chrome_sandbox'

DEST_DIR = 'gtest_results'

HTTPD_CONF = {
    'linux': 'httpd2_linux.conf',
    'mac': 'httpd2_mac.conf',
    'win': 'httpd.conf'
}


def should_enable_sandbox(sandbox_path):
  """Return a boolean indicating that the current slave is capable of using the
  sandbox and should enable it.  This should return True iff the slave is a
  Linux host with the sandbox file present and configured correctly."""
  if not (sys.platform.startswith('linux') and
          os.path.exists(sandbox_path)):
    return False
  sandbox_stat = os.stat(sandbox_path)
  if ((sandbox_stat.st_mode & stat.S_ISUID) and
      (sandbox_stat.st_mode & stat.S_IRUSR) and
      (sandbox_stat.st_mode & stat.S_IXUSR) and
      (sandbox_stat.st_uid == 0)):
    return True
  return False


def get_temp_count():
  """Returns the number of files and directories inside the temporary dir."""
  return len(os.listdir(tempfile.gettempdir()))


def _RunGTestCommand(command, results_tracker=None, pipes=None):
  if results_tracker:
    return chromium_utils.RunCommand(
        command, pipes=pipes, parser_func=results_tracker.ProcessLine)
  else:
    return chromium_utils.RunCommand(command, pipes=pipes)


def _GetMaster():
  return slave_utils.GetActiveMaster()


def _GetMasterString(master):
  return '[Running for master: "%s"]' % master


def _GenerateJSONForTestResults(options, results_tracker):
  """Generate (update) a JSON file from the gtest results XML and
  upload the file to the archive server.
  The archived JSON file will be placed at:
  www-dir/DEST_DIR/buildname/testname/results.json
  on the archive server (NOTE: this is to be deprecated).
  Note that it adds slave's WebKit/Tools/Scripts to the PYTHONPATH
  to run the JSON generator.

  Args:
    options: command-line options that are supposed to have build_dir,
        results_directory, builder_name, build_name and test_output_xml values.
  """
  # pylint: disable=W0703
  results_map = None
  try:
    if os.path.exists(options.test_output_xml):
      results_map = gtest_slave_utils.GetResultsMapFromXML(
          options.test_output_xml)
    else:
      sys.stderr.write('Unable to generate JSON from XML, using log output.')
      # The file did not get generated. See if we can generate a results map
      # from the log output.
      results_map = gtest_slave_utils.GetResultsMap(results_tracker)
  except Exception, e:
    # This error will be caught by the following 'not results_map' statement.
    print 'Error: ', e

  if not results_map:
    print 'No data was available to update the JSON results'
    return

  build_dir = os.path.abspath(options.build_dir)
  slave_name = slave_utils.SlaveBuildName(build_dir)

  generate_json_options = copy.copy(options)
  generate_json_options.build_name = slave_name
  generate_json_options.input_results_xml = options.test_output_xml
  generate_json_options.builder_base_url = '%s/%s/%s/%s' % (
      config.Master.archive_url, DEST_DIR, slave_name, options.test_type)
  generate_json_options.master_name = _GetMaster()
  generate_json_options.test_results_server = config.Master.test_results_server

  # Print out master name for log_parser
  print _GetMasterString(generate_json_options.master_name)

  try:
    # Set webkit and chrome directory (they are used only to get the
    # repository revisions).
    generate_json_options.webkit_dir = chromium_utils.FindUpward(
        build_dir, 'third_party', 'WebKit', 'Source')
    generate_json_options.chrome_dir = build_dir

    # Generate results JSON file and upload it to the appspot server.
    gtest_slave_utils.GenerateAndUploadJSONResults(
        results_map, generate_json_options)

    # The code can throw all sorts of exceptions, including
    # slave.gtest.networktransaction.NetworkTimeout so just trap everything.
  except:  # pylint: disable=W0702
    print 'Unexpected error while generating JSON'


def _BuildParallelCommand(build_dir, test_exe_path, options):
  supervisor_path = os.path.join(build_dir, '..', 'tools',
                                 'sharding_supervisor',
                                 'sharding_supervisor.py')
  supervisor_args = ['--no-color']
  if options.factory_properties.get('retry_failed', True):
    supervisor_args.append('--retry-failed')
  if options.total_shards and options.shard_index:
    supervisor_args.extend(['--total-slaves', str(options.total_shards),
                            '--slave-index', str(options.shard_index - 1)])
  if options.sharding_args:
    supervisor_args.extend(options.sharding_args.split())
  command = [sys.executable, supervisor_path]
  command.extend(supervisor_args)
  command.append(test_exe_path)
  return command


def start_http_server(platform, build_dir, test_exe_path, document_root):
  # pylint: disable=F0401
  import google.httpd_utils
  import google.platform_utils
  platform_util = google.platform_utils.PlatformUtility(build_dir)

  # Name the output directory for the exe, without its path or suffix.
  # e.g., chrome-release/httpd_logs/unit_tests/
  test_exe_name = os.path.splitext(os.path.basename(test_exe_path))[0]
  output_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir),
                            'httpd_logs',
                            test_exe_name)

  # Sanity checks for httpd2_linux.conf.
  if platform == 'linux':
    for ssl_file in ['ssl.conf', 'ssl.load']:
      ssl_path = os.path.join('/etc/apache/mods-enabled', ssl_file)
      if not os.path.exists(ssl_path):
        sys.stderr.write('WARNING: %s missing, http server may not start\n' %
                         ssl_path)
    if not os.access('/var/run/apache2', os.W_OK):
      sys.stderr.write('WARNING: cannot write to /var/run/apache2, '
                       'http server may not start\n')

  apache_config_dir = google.httpd_utils.ApacheConfigDir(build_dir)
  httpd_conf_path = os.path.join(apache_config_dir, HTTPD_CONF[platform])
  mime_types_path = os.path.join(apache_config_dir, 'mime.types')
  document_root = os.path.abspath(document_root)

  start_cmd = platform_util.GetStartHttpdCommand(output_dir,
                                                 httpd_conf_path,
                                                 mime_types_path,
                                                 document_root)
  stop_cmd = platform_util.GetStopHttpdCommand()
  http_server = google.httpd_utils.ApacheHttpd(start_cmd, stop_cmd, [8000])
  try:
    http_server.StartServer()
  except google.httpd_utils.HttpdNotStarted, e:
    raise google.httpd_utils.HttpdNotStarted('%s. See log file in %s' %
                                             (e, output_dir))
  return http_server


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


def get_parsers():
  parsers = {'gtest': gtest_utils.GTestLogParser,
             'benchpress': process_log_utils.BenchpressLogProcessor,
             'playback': process_log_utils.PlaybackLogProcessor,
             'graphing': process_log_utils.GraphingLogProcessor,
             'endure': process_log_utils.GraphingEndureLogProcessor,
             'framerate': process_log_utils.GraphingFrameRateLogProcessor,
             'pagecycler': process_log_utils.GraphingPageCyclerLogProcessor}
  return parsers


def list_parsers(selection):
  parsers = get_parsers()
  shouldlist = selection and selection == 'list'
  if shouldlist:
    print
    print 'Available log parsers:'
    for p in parsers:
      print ' ', p, parsers[p].__name__

  return shouldlist


def select_results_tracker(selection, use_gtest):
  parsers = get_parsers()
  if selection:
    if selection in parsers:
      if use_gtest and selection != 'gtest':
        raise NotImplementedError("'%s' doesn't make sense with "
                                  "options.generate_json_file")
      else:
        return parsers[selection]
    else:
      raise KeyError("'%s' is not a valid GTest parser!!" % selection)
  elif use_gtest:
    return parsers['gtest']
  return None


def create_results_tracker(tracker_class, options):
  if not tracker_class:
    return None

  if tracker_class.__name__ == 'GTestLogParser':
    tracker_obj = tracker_class()
  else:
    build_dir = os.path.abspath(options.build_dir)
    webkit_dir = chromium_utils.FindUpward(build_dir, 'third_party', 'WebKit',
                                           'Source')

    tracker_obj = tracker_class(
        revision=GetSvnRevision(os.path.dirname(build_dir)),
        build_property=options.build_properties,
        factory_properties=options.factory_properties,
        webkit_revision=GetSvnRevision(webkit_dir))

  if options.annotate and options.generate_json_file:
    tracker_obj.ProcessLine(_GetMasterString(_GetMaster()))

  return tracker_obj


def annotate(test_name, result, results_tracker, full_name=False,
             perf_dashboard_id=None):
  """Given a test result and tracker, update the waterfall with test results."""
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
  elif result == process_log_utils.WARNINGS:
    print '@@@STEP_WARNINGS@@@'
  else:
    print '@@@STEP_FAILURE@@@'
    get_text_result = process_log_utils.FAILURE

  for desc in getText(get_text_result, results_tracker, test_name):
    print '@@@STEP_TEXT@%s@@@' % desc

  if hasattr(results_tracker, 'PerformanceLogs'):
    if not perf_dashboard_id:
      print 'runtest.py error: perf step specified but',
      print 'no test_id in factory_properties!'
      print '@@@STEP_EXCEPTION@@@'
      return
    for logname, log in results_tracker.PerformanceLogs().iteritems():
      lines = [str(l).rstrip() for l in log]
      slave_utils.WriteLogLines(logname, lines, perf=perf_dashboard_id)


def get_build_dir_and_exe_path_mac(options, target_dir, exe_name):
  """Returns a tuple of the build dir and path to the executable in the
     specified target directory.

     Args:
       target_dir: the target directory where the executable should be found
           (e.g. 'Debug' or 'Release-iphonesimulator').
       exe_name: the name of the executable file in the target directory.
  """
  build_dir = os.path.normpath(os.path.abspath(options.build_dir))
  exe_path = os.path.join(build_dir, target_dir, exe_name)
  if not os.path.exists(exe_path):
    pre = 'Unable to find %s\n' % exe_path

    build_dir = os.path.dirname(build_dir)
    outdir = 'xcodebuild'
    is_make_or_ninja = (options.factory_properties.get('gclient_env', {})
                        .get('GYP_GENERATORS', '') in ('ninja', 'make'))
    if is_make_or_ninja:
      outdir = 'out'

    build_dir = os.path.join(build_dir, outdir)
    exe_path = os.path.join(build_dir, target_dir, exe_name)
    if not os.path.exists(exe_path):
      msg = pre + 'Unable to find %s' % exe_path
      if options.factory_properties.get('succeed_on_missing_exe', False):
        print '%s missing but succeed_on_missing_exe used, exiting' % (
            exe_path)
        return 0
      raise chromium_utils.PathNotFound(msg)

  return build_dir, exe_path


def upload_profiling_data(options, args):
  """Using the target build configuration, archive the profiling data to Google
  Storage.
  """
  # args[1] has --gtest-filter argument.
  if len(args) < 2:
    return 0

  builder_name = options.build_properties.get('buildername')
  # Disabled uploading profile data (added a non-existing builder_name).
  if (builder_name != 'XP Interactive Perf1' or
      options.build_properties.get('mastername') != 'chromium.perf' or
      not options.build_properties.get('got_revision')):
    return 0

  gtest_filter = args[1]
  if (gtest_filter is None):
    return 0
  gtest_name = ''
  if (gtest_filter.find('StartupTest.*:ShutdownTest.*') > -1):
    gtest_name = 'StartupTest'
  else:
    return 0

  build_dir = os.path.normpath(os.path.abspath(options.build_dir))

  # archive_profiling_data.py is in /b/build/scripts/slave and
  # build_dir is /b/build/slave/SLAVE_NAME/build/src/build.
  profiling_archive_tool = os.path.join(build_dir, '..', '..', '..', '..', '..',
                                        'scripts', 'slave',
                                        'archive_profiling_data.py')

  if sys.platform == 'win32':
    python = 'python_slave'
  else:
    python = 'python'

  revision = options.build_properties.get('got_revision')
  cmd = [python, profiling_archive_tool, '--revision', revision,
         '--build-dir', build_dir, '--builder-name', builder_name,
         '--test-name', gtest_name]

  return chromium_utils.RunCommand(cmd)


def main_mac(options, args):
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  test_exe = args[0]
  if options.run_python_script:
    build_dir = os.path.normpath(os.path.abspath(options.build_dir))
    test_exe_path = test_exe
  else:
    build_dir, test_exe_path = get_build_dir_and_exe_path_mac(options,
                                                              options.target,
                                                              test_exe)

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  if options.parallel:
    command = _BuildParallelCommand(build_dir, test_exe_path, options)
  elif options.run_shell_script:
    command = ['bash', test_exe_path]
  elif options.run_python_script:
    command = [sys.executable, test_exe]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  if list_parsers(options.annotate):
    return 0
  tracker_class = select_results_tracker(options.annotate,
                                         options.generate_json_file)
  results_tracker = create_results_tracker(tracker_class, options)

  if options.generate_json_file:
    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  try:
    http_server = None
    if options.document_root:
      http_server = start_http_server('mac', build_dir=build_dir,
                                      test_exe_path=test_exe_path,
                                      document_root=options.document_root)
    pipes = []
    if options.factory_properties.get('asan', False):
      symbolize = os.path.abspath(os.path.join('src', 'tools', 'valgrind',
                                               'asan', 'asan_symbolize.py'))
      pipes = [[sys.executable, symbolize], ['c++filt']]

    result = _RunGTestCommand(command, pipes=pipes,
                              results_tracker=results_tracker)
  finally:
    if http_server:
      http_server.StopServer()

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  if options.annotate:
    annotate(options.test_type, result, results_tracker,
             options.factory_properties.get('full_test_name'),
             perf_dashboard_id=options.factory_properties.get(
                 'test_name'))

  return result


def main_ios(options, args):
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  def kill_simulator():
    chromium_utils.RunCommand(['/usr/bin/killall', 'iPhone Simulator'])

  # For iOS tests, the args come in in the following order:
  #   [0] test display name formatted as 'test_name (device[ ios_version])'
  #   [1:] gtest args (e.g. --gtest_print_time)

  # Default to running on iPhone with iOS version 5.1.
  device = 'iphone'
  ios_version = '6.0'

  # Parse the test_name and device from the test display name.
  # The expected format is: <test_name> (<device>)
  result = re.match(r'(.*) \((.*)\)$', args[0])
  if result is not None:
    test_name, device = result.groups()
    # Check if the device has an iOS version. The expected format is:
    # <device_name><space><ios_version>, where ios_version may have 2 or 3
    # numerals (e.g. '4.3.11' or '5.0').
    result = re.match(r'(.*) (\d+\.\d+(\.\d+)?)$', device)
    if result is not None:
      device = result.groups()[0]
      ios_version = result.groups()[1]
  else:
    # If first argument is not in the correct format, log a warning but
    # fall back to assuming the first arg is the test_name and just run
    # on the iphone simulator.
    test_name = args[0]
    print ('Can\'t parse test name, device, and iOS version. '
           'Running %s on %s %s' % (test_name, device, ios_version))

  # Build the args for invoking iossim, which will install the app on the
  # simulator and launch it, then dump the test results to stdout.

  # Note that the first object (build_dir) returned from the following
  # method invocations is ignored because only the app executable is needed.
  _, app_exe_path = get_build_dir_and_exe_path_mac(
      options,
      options.target + '-iphonesimulator',
      test_name + '.app')

  _, test_exe_path = get_build_dir_and_exe_path_mac(options,
                                                    options.target,
                                                    'iossim')
  command = [test_exe_path,
      '-d', device,
      '-s', ios_version,
      app_exe_path, '--'
  ]
  command.extend(args[1:])

  if list_parsers(options.annotate):
    return 0
  results_tracker = create_results_tracker(get_parsers()['gtest'], options)

  # Make sure the simulator isn't running.
  kill_simulator()

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  dirs_to_cleanup = []
  crash_files_before = set([])
  crash_files_after = set([])
  crash_files_before = set(crash_utils.list_crash_logs())

  result = _RunGTestCommand(command, results_tracker)

  # Because test apps kill themselves, iossim sometimes returns non-zero
  # status even though all tests have passed.  Check the results_tracker to
  # see if the test run was successful.
  if results_tracker.CompletedWithoutFailure():
    result = 0
  else:
    result = 1

  if result != 0:
    crash_utils.wait_for_crash_logs()
  crash_files_after = set(crash_utils.list_crash_logs())

  kill_simulator()

  new_crash_files = crash_files_after.difference(crash_files_before)
  crash_utils.print_new_crash_files(new_crash_files)

  for a_dir in dirs_to_cleanup:
    try:
      chromium_utils.RemoveDirectory(a_dir)
    except OSError, e:
      print >> sys.stderr, e
      # Don't fail.

  return result


def main_linux(options, args):
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  build_dir = os.path.normpath(os.path.abspath(options.build_dir))
  slave_name = slave_utils.SlaveBuildName(build_dir)
  # If this is a sub-project build (i.e. there's a 'sconsbuild' in build_dir),
  # look for the test binaries there, otherwise look for the top-level build
  # output.
  # This assumes we never pass a build_dir which might contain build output that
  # we're not trying to test. This is currently a safe assumption since we don't
  # have any builders that do both sub-project and top-level builds (only
  # Modules builders do sub-project builds), so they shouldn't ever have both
  # 'build_dir/sconsbuild' and 'build_dir/../sconsbuild'.
  outdir = None
  if os.path.exists(os.path.join(build_dir, 'sconsbuild')):
    outdir = 'sconsbuild'
  elif os.path.exists(os.path.join(build_dir, 'out')):
    outdir = 'out'

  if outdir:
    bin_dir = os.path.join(build_dir, outdir, options.target)
    src_dir = os.path.join(slave_utils.SlaveBaseDir(build_dir), 'build', 'src')
    os.environ['CR_SOURCE_ROOT'] = src_dir
  else:
    if os.path.exists(os.path.join(build_dir, '..', 'sconsbuild')):
      bin_dir = os.path.join(build_dir, '..', 'sconsbuild', options.target)
    else:
      bin_dir = os.path.join(build_dir, '..', 'out', options.target)

  # Figure out what we want for a special frame buffer directory.
  special_xvfb_dir = None
  if options.special_xvfb == 'auto':
    fp_special_xvfb = options.factory_properties.get('special_xvfb', None)
    fp_chromeos = options.factory_properties.get('chromeos', None)
    if fp_special_xvfb or (fp_special_xvfb is None and (fp_chromeos or
        slave_utils.GypFlagIsOn(options, 'use_aura') or
        slave_utils.GypFlagIsOn(options, 'chromeos'))):
      special_xvfb_dir = options.special_xvfb_dir
  elif options.special_xvfb:
    special_xvfb_dir = options.special_xvfb_dir

  test_exe = args[0]
  if options.run_python_script:
    test_exe_path = test_exe
  else:
    test_exe_path = os.path.join(bin_dir, test_exe)
  if not os.path.exists(test_exe_path):
    if options.factory_properties.get('succeed_on_missing_exe', False):
      print '%s missing but succeed_on_missing_exe used, exiting' % (
          test_exe_path)
      return 0
    msg = 'Unable to find %s' % test_exe_path
    raise chromium_utils.PathNotFound(msg)

  # Unset http_proxy and HTTPS_PROXY environment variables.  When set, this
  # causes some tests to hang.  See http://crbug.com/139638 for more info.
  if 'http_proxy' in os.environ:
    del(os.environ['http_proxy'])
    print 'Deleted http_proxy environment variable.'
  if 'HTTPS_PROXY' in os.environ:
    del(os.environ['HTTPS_PROXY'])
    print 'Deleted HTTPS_PROXY environment variable.'

  # Decide whether to enable the suid sandbox for Chrome.
  if (should_enable_sandbox(CHROME_SANDBOX_PATH) and
      not options.factory_properties.get('asan', False) and
      not options.factory_properties.get('tsan', False)):
    print 'Enabling sandbox.  Setting environment variable:'
    print '  CHROME_DEVEL_SANDBOX="%s"' % CHROME_SANDBOX_PATH
    os.environ['CHROME_DEVEL_SANDBOX'] = CHROME_SANDBOX_PATH
  else:
    print 'Disabling sandbox.  Setting environment variable:'
    print '  CHROME_DEVEL_SANDBOX=""'
    os.environ['CHROME_DEVEL_SANDBOX'] = ''

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  os.environ['LD_LIBRARY_PATH'] = '%s:%s/lib:%s/lib.target' % (bin_dir, bin_dir,
                                                               bin_dir)
  # Figure out what we want for a special llvmpipe directory.
  if options.llvmpipe_dir and os.path.exists(options.llvmpipe_dir):
    os.environ['LD_LIBRARY_PATH'] += ':' + options.llvmpipe_dir

  if options.parallel:
    command = _BuildParallelCommand(build_dir, test_exe_path, options)
  elif options.run_shell_script:
    command = ['bash', test_exe_path]
  elif options.run_python_script:
    command = [sys.executable, test_exe]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  if list_parsers(options.annotate):
    return 0
  tracker_class = select_results_tracker(options.annotate,
                                         options.generate_json_file)
  results_tracker = create_results_tracker(tracker_class, options)

  if options.generate_json_file:
    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  try:
    http_server = None
    if options.document_root:
      http_server = start_http_server('linux', build_dir=build_dir,
                                      test_exe_path=test_exe_path,
                                      document_root=options.document_root)
    if options.xvfb:
      xvfb.StartVirtualX(
          slave_name, bin_dir,
          with_wm=options.factory_properties.get('window_manager', True),
          server_dir=special_xvfb_dir)

    pipes = []
    if options.factory_properties.get('asan', False):
      symbolize = os.path.abspath(os.path.join('src', 'tools', 'valgrind',
                                               'asan', 'asan_symbolize.py'))
      pipes = [[sys.executable, symbolize], ['c++filt']]

    result = _RunGTestCommand(command, pipes=pipes,
                              results_tracker=results_tracker)
  finally:
    if http_server:
      http_server.StopServer()
    if options.xvfb:
      xvfb.StopVirtualX(slave_name)

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  if options.annotate:
    annotate(options.test_type, result, results_tracker,
             options.factory_properties.get('full_test_name'),
             perf_dashboard_id=options.factory_properties.get(
                 'test_name'))

  return result


def main_win(options, args):
  """Using the target build configuration, run the executable given in the
  first non-option argument, passing any following arguments to that
  executable.
  """
  if len(args) < 1:
    raise chromium_utils.MissingArgument('Usage: %s' % USAGE)

  test_exe = args[0]
  build_dir = os.path.abspath(options.build_dir)
  if options.run_python_script:
    test_exe_path = test_exe
  else:
    test_exe_path = os.path.join(build_dir, options.target, test_exe)

  if not os.path.exists(test_exe_path):
    if options.factory_properties.get('succeed_on_missing_exe', False):
      print '%s missing but succeed_on_missing_exe used, exiting' % (
          test_exe_path)
      return 0
    raise chromium_utils.PathNotFound('Unable to find %s' % test_exe_path)

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'chrome.exe', True)

  if options.parallel:
    command = _BuildParallelCommand(build_dir, test_exe_path, options)
  elif options.run_python_script:
    command = [sys.executable, test_exe]
  else:
    command = [test_exe_path]
  command.extend(args[1:])

  # Nuke anything that appears to be stale chrome items in the temporary
  # directory from previous test runs (i.e.- from crashes or unittest leaks).
  slave_utils.RemoveChromeTemporaryFiles()

  if list_parsers(options.annotate):
    return 0
  tracker_class = select_results_tracker(options.annotate,
                                         options.generate_json_file)
  results_tracker = create_results_tracker(tracker_class, options)

  if options.generate_json_file:
    if os.path.exists(options.test_output_xml):
      # remove the old XML output file.
      os.remove(options.test_output_xml)

  try:
    http_server = None
    if options.document_root:
      http_server = start_http_server('win', build_dir=build_dir,
                                      test_exe_path=test_exe_path,
                                      document_root=options.document_root)
    result = _RunGTestCommand(command, results_tracker)
  finally:
    if http_server:
      http_server.StopServer()

  if options.enable_pageheap:
    slave_utils.SetPageHeap(build_dir, 'chrome.exe', False)

  if options.generate_json_file:
    _GenerateJSONForTestResults(options, results_tracker)

  if options.annotate:
    annotate(options.test_type, result, results_tracker,
             options.factory_properties.get('full_test_name'),
             perf_dashboard_id=options.factory_properties.get(
                 'test_name'))

  return result


def main():
  import platform

  xvfb_path = os.path.join(os.path.dirname(sys.argv[0]), '..', '..',
                           'third_party', 'xvfb', platform.architecture()[0])

  # Initialize logging.
  log_level = logging.INFO
  logging.basicConfig(level=log_level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  option_parser = optparse.OptionParser(usage=USAGE)

  # Since the trailing program to run may have has command-line args of its
  # own, we need to stop parsing when we reach the first positional argument.
  option_parser.disable_interspersed_args()

  option_parser.add_option('', '--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--enable-pageheap', action='store_true',
                           default=False,
                           help='enable pageheap checking for chrome.exe')
  # --with-httpd assumes a chromium checkout with src/tools/python.
  option_parser.add_option('', '--with-httpd', dest='document_root',
                           default=None, metavar='DOC_ROOT',
                           help='Start a local httpd server using the given '
                                'document root, relative to the current dir')
  option_parser.add_option('', '--total-shards', dest='total_shards',
                           default=None, type='int',
                           help='Number of shards to split this test into.')
  option_parser.add_option('', '--shard-index', dest='shard_index',
                           default=None, type='int',
                           help='Shard to run. Must be between 1 and '
                                'total-shards.')
  option_parser.add_option('', '--run-shell-script', action='store_true',
                           default=False,
                           help='treat first argument as the shell script'
                                'to run.')
  option_parser.add_option('', '--run-python-script', action='store_true',
                           default=False,
                           help='treat first argument as a python script'
                                'to run.')
  option_parser.add_option('', '--generate-json-file', action='store_true',
                           default=False,
                           help='output JSON results file if specified.')
  option_parser.add_option('', '--parallel', action='store_true',
                           help='Shard and run tests in parallel for speed '
                                'with sharding_supervisor.')
  option_parser.add_option('', '--llvmpipe', action='store_const',
                           const=xvfb_path, dest='llvmpipe_dir',
                           help='Use software gpu pipe directory.')
  option_parser.add_option('', '--no-llvmpipe', action='store_const',
                           const=None, dest='llvmpipe_dir',
                           help='Do not use software gpu pipe directory.')
  option_parser.add_option('', '--llvmpipe-dir',
                           default=None, dest='llvmpipe_dir',
                           help='Path to software gpu library directory.')
  option_parser.add_option('', '--special-xvfb-dir', default=xvfb_path,
                           help='Path to virtual X server directory on Linux.')
  option_parser.add_option('', '--special-xvfb', action='store_true',
                           default='auto',
                           help='use non-default virtual X server on Linux.')
  option_parser.add_option('', '--no-special-xvfb', action='store_false',
                           dest='special_xvfb',
                           help='Use default virtual X server on Linux.')
  option_parser.add_option('', '--auto-special-xvfb', action='store_const',
                           const='auto', dest='special_xvfb',
                           help='Guess as to virtual X server on Linux.')
  option_parser.add_option('', '--xvfb', action='store_true', dest='xvfb',
                           default=True,
                           help='Start virtual X server on Linux.')
  option_parser.add_option('', '--no-xvfb', action='store_false', dest='xvfb',
                           help='Do not start virtual X server on Linux.')
  option_parser.add_option('', '--sharding-args', dest='sharding_args',
                           default=None,
                           help='Options to pass to sharding_supervisor.')
  option_parser.add_option('-o', '--results-directory', default='',
                           help='output results directory for JSON file.')
  option_parser.add_option('', '--builder-name', default=None,
                           help='The name of the builder running this script.')
  option_parser.add_option('', '--build-number', default=None,
                           help=('The build number of the builder running'
                                 'this script.'))
  option_parser.add_option('', '--test-type', default='',
                           help='The test name that identifies the test, '
                                'e.g. \'unit-tests\'')
  option_parser.add_option('', '--test-results-server', default='',
                           help='The test results server to upload the '
                                'results.')
  option_parser.add_option('', '--annotate', default='',
                           help='Annotate output when run as a buildstep. '
                                'Specify which type of test to parse, available'
                                ' types listed with --annotate=list.')
  chromium_utils.AddPropertiesOptions(option_parser)
  options, args = option_parser.parse_args()

  options.test_type = options.test_type or options.factory_properties.get(
      'step_name')

  if options.run_shell_script and options.run_python_script:
    sys.stderr.write('Use either --run-shell-script OR --run-python-script, '
                     'not both.')
    return 1

  # Print out builder name for log_parser
  print '[Running on builder: "%s"]' % options.builder_name

  if (options.factory_properties.get('asan', False) or
      options.factory_properties.get('tsan', False)):
    # Instruct GTK to use malloc while running ASan or TSan tests.
    os.environ['G_SLICE'] = 'always-malloc'
    os.environ['NSS_DISABLE_ARENA_FREE_LIST'] = '1'
    os.environ['NSS_DISABLE_UNLOAD'] = '1'
    # Disable ASLR on Mac when running ASAN tests.
    os.environ['DYLD_NO_PIE'] = '1'

  # TODO(glider): remove the symbolizer path once
  # https://code.google.com/p/address-sanitizer/issues/detail?id=134 is fixed.
  symbolizer_path = os.path.abspath(os.path.join('src', 'third_party',
      'llvm-build', 'Release+Asserts', 'bin', 'llvm-symbolizer'))
  tsan_options = ('suppressions=src/tools/valgrind/tsan_v2/suppressions.txt '
                  'report_signal_unsafe=0 '
                  'report_thread_leaks=0 '
                  'external_symbolizer_path=%s' % symbolizer_path)
  if options.factory_properties.get('tsan', False):
    os.environ['TSAN_OPTIONS'] = tsan_options
  # Set the number of shards environement variables.
  if options.total_shards and options.shard_index:
    os.environ['GTEST_TOTAL_SHARDS'] = str(options.total_shards)
    os.environ['GTEST_SHARD_INDEX'] = str(options.shard_index - 1)

  if options.results_directory:
    options.test_output_xml = os.path.normpath(os.path.join(
        options.results_directory, '%s.xml' % options.test_type))
    args.append('--gtest_output=xml:' + options.test_output_xml)

  temp_files = get_temp_count()
  if sys.platform.startswith('darwin'):
    test_platform = options.factory_properties.get('test_platform', '')
    if test_platform in ('ios-simulator',):
      result = main_ios(options, args)
    else:
      result = main_mac(options, args)
  elif sys.platform == 'win32':
    result = main_win(options, args)
  elif sys.platform == 'linux2':
    result = main_linux(options, args)
  else:
    sys.stderr.write('Unknown sys.platform value %s\n' % repr(sys.platform))
    return 1

  upload_profiling_data(options, args)

  new_temp_files = get_temp_count()
  if temp_files > new_temp_files:
    print >> sys.stderr, (
        'Confused: %d files were deleted from %s during the test run') % (
            (temp_files - new_temp_files), tempfile.gettempdir())
  elif temp_files < new_temp_files:
    print >> sys.stderr, (
        '%d new files were left in %s: Fix the tests to clean up themselves.'
        ) % ((new_temp_files - temp_files), tempfile.gettempdir())
    # TODO(maruel): Make it an error soon. Not yet since I want to iron out all
    # the remaining cases before.
    #result = 1
  return result


if '__main__' == __name__:
  sys.exit(main())
