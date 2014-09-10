#! /usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set up and invoke telemetry tests."""

import json
import optparse
import os
import sys

from common import chromium_utils
from slave import build_directory


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _GetPythonTestCommand(py_script, target, arg_list=None,
                          wrapper_args=None, fp=None):
  """Synthesizes a command line to run runtest.py."""
  cmd = [sys.executable,
         os.path.join(SCRIPT_DIR, 'slave', 'runtest.py'),
         '--run-python-script',
         '--target', target,
         '--no-xvfb'] #  telemetry.py should be run by a 'master' runtest.py
                      #  which starts xvfb on linux.
  if fp:
    cmd.extend(["--factory-properties=%s" % json.dumps(fp)])
  if wrapper_args is not None:
    cmd.extend(wrapper_args)
  cmd.append(py_script)

  if arg_list is not None:
    cmd.extend(arg_list)
  return cmd


def _GetReferenceBuildPath(target_os, target_platform):
  ref_dir = os.path.join('src', 'chrome', 'tools', 'test', 'reference_build')
  if target_os == 'android':
    # TODO(tonyg): Check in a reference android content shell.
    return None
  elif target_platform == 'win32':
    return os.path.join(ref_dir, 'chrome_win', 'chrome.exe')
  elif target_platform == 'darwin':
    return os.path.join(ref_dir, 'chrome_mac', 'Google Chrome.app', 'Contents',
        'MacOS', 'Google Chrome')
  elif target_platform.startswith('linux'):
    return os.path.join(ref_dir, 'chrome_linux', 'chrome')
  return None


def _GenerateTelemetryCommandSequence(options):
  """Given a test name, page set, and target, generate a telemetry test seq."""
  fp = options.factory_properties
  test_name = fp.get('test_name')
  extra_args = fp.get('extra_args')
  target = fp.get('target')
  target_os = fp.get('target_os')
  target_platform = fp.get('target_platform')
  profile_type = fp.get('profile_type')
  build_dir = build_directory.GetBuildOutputDirectory()

  script = os.path.join(fp.get('tools_dir')
                            or os.path.join('src', 'tools'),
                        'perf', 'run_benchmark')
  browser_exe = fp.get('browser_exe')

  test_specification = [test_name]

  env = os.environ

  # List of command line arguments common to all test platforms.
  common_args = [
      # INFO level verbosity.
      '-v',
      # Output results in the format the buildbot expects.
      '--output-format=buildbot',
      ]

  if profile_type:
    profile_dir = os.path.join(
        build_dir, target, 'generated_profile', profile_type)
    common_args.append('--profile-dir=' + profile_dir)
  if extra_args:
    common_args.extend(extra_args)

  commands = []

  # Run the test against the target chrome build.
  browser = target.lower()
  wrapper_args = None
  if target_os == 'android':
    browser = options.target_android_browser
    target_flag = '--%s' % target.lower()
    wrapper_args = ['src/build/android/test_runner.py', 'perf', '-v',
                    target_flag,
                    '--single-step',
                    '--']
  # If an executable is passed, use that instead.
  if browser_exe:
    browser_info = ['--browser=exact',
                    '--browser-executable=%s' % browser_exe]
  else:
    browser_info = ['--browser=%s' % browser]
  test_args = list(common_args)
  test_args.extend(browser_info)
  test_args.extend(test_specification)
  test_cmd = _GetPythonTestCommand(script, target, test_args,
                                   wrapper_args=wrapper_args, fp=fp)
  commands.append(test_cmd)

  # Run the test against the target chrome build for different user profiles on
  # certain page cyclers.
  if target_os != 'android':
    if test_name in ('page_cycler_moz', 'page_cycler_morejs'):
      test_args = list(common_args)
      test_args.extend(['--profile-type=typical_user',
                        '--output-trace-tag=_extcs1'])
      test_args.extend(browser_info)
      test_args.extend(test_specification)
      test_cmd = _GetPythonTestCommand(script, target, test_args, fp=fp)
      commands.append(test_cmd)
    if test_name in ('page_cycler_moz', 'page_cycler_morejs'):
      test_args = list(common_args)
      test_args.extend(['--profile-type=power_user',
                        '--output-trace-tag=_extwr'])
      test_args.extend(browser_info)
      test_args.extend(test_specification)
      test_cmd = _GetPythonTestCommand(script, target, test_args, fp=fp)
      commands.append(test_cmd)

  # Run the test against the reference build on platforms where it exists.
  ref_build = _GetReferenceBuildPath(target_os, target_platform)
  ref_build = fp.get('reference_build_executable', ref_build)
  if ref_build and fp.get('run_reference_build', True):
    ref_args = list(common_args)
    ref_args.extend(['--browser=exact',
                '--browser-executable=%s' % ref_build,
                '--output-trace-tag=_ref'])
    ref_args.extend(test_specification)
    ref_cmd = _GetPythonTestCommand(script, target, ref_args, fp=fp)
    commands.append(ref_cmd)

  return commands, env


def main(argv):
  prog_desc = 'Invoke telemetry performance tests.'
  parser = optparse.OptionParser(usage=('%prog [options]' + '\n\n' + prog_desc))
  parser.add_option('--print-cmd', action='store_true',
                    help='only print command instead of running it')
  parser.add_option('--target-android-browser',
                    default='android-chrome-shell',
                    help='target browser used on Android')
  parser.add_option('--factory-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='factory properties in JSON format')

  options, _ = parser.parse_args(argv[1:])
  if not options.factory_properties:
    print 'This program requires a factory properties to run.'
    return 1

  commands, env = _GenerateTelemetryCommandSequence(options)

  retval = 0
  for command in commands:
    if options.print_cmd:
      print ' '.join("'%s'" % c for c in command)
      continue

    retval = chromium_utils.RunCommand(command, env=env)
    if retval != 0:
      break
  return retval


if '__main__' == __name__:
  sys.exit(main(sys.argv))
