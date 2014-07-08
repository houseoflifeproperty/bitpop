#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Script for creating coverage.info file with dynamorio bbcov2lcov binary.
"""

import glob
import optparse
import os
import subprocess
import sys

from common import chromium_utils
from slave import build_directory

# Method could be a function
# pylint: disable=R0201

COVERAGE_DIR_POSTFIX = '_coverage'
COVERAGE_INFO = 'coverage.info'


def GetExecutableName(executable):
  """The executable name must be executable plus '.exe' on Windows, or else
  just the test name."""
  if sys.platform == 'win32':
    return executable + '.exe'
  return executable


def RunCmd(command, env=None, shell=True):
  """Call a shell command.
  Args:
    command: the command to run
    env: dictionary of environment variables

  Returns:
    retcode
  """
  process = subprocess.Popen(command, shell=shell, env=env)
  process.wait()
  return process.returncode


def DynamorioLogDir():
  profile = os.getenv("USERPROFILE")
  if not profile:
    raise Exception('USERPROFILE envir var not found')
  if chromium_utils.IsWindows():
    return profile + '\\AppData\\LocalLow\\coverage'
  else:
    return profile + '\\coverage'


def PreProcess(options):
  """Setup some dynamorio config before running tests."""
  dynamorio_log_dir = DynamorioLogDir()
  chromium_utils.RemoveDirectory(dynamorio_log_dir)
  chromium_utils.MaybeMakeDirectory(dynamorio_log_dir)
  drrun_config = ('DR_OP=-nop_initial_bblock -disable_traces '
                  '-fast_client_decode -no_enable_reset\n'
                  'CLIENT_REL=tools/lib32/release/bbcov.dll\n'
                  'TOOL_OP=-logdir ' + dynamorio_log_dir + '\n')
  fhandler = open(os.path.join(options.dynamorio_dir, 'tools',
                               'bbcov.drrun32'), 'w+')
  fhandler.write(drrun_config)

  # Exclude python's execution
  chromium_utils.RunCommand(os.path.join(options.dynamorio_dir, 'bin32',
                                         'drconfig -reg python.exe -norun'))
  return 0


def CreateCoverageFileAndUpload(options):
  """Create coverage file with bbcov2lcov binary and upload to www dir."""
  # Assert log files exist
  dynamorio_log_dir = DynamorioLogDir()
  log_files = glob.glob(os.path.join(dynamorio_log_dir, '*.log'))
  if not log_files:
    print 'No coverage log files found.'
    return 1

  if (options.browser_shard_index and
      options.test_to_upload in options.sharded_tests):
    coverage_info = os.path.join(
        options.build_dir, 'coverage_%s.info' % options.browser_shard_index)
  else:
    coverage_info = os.path.join(options.build_dir, COVERAGE_INFO)
  coverage_info = os.path.normpath(coverage_info)
  if os.path.isfile(coverage_info):
    os.remove(coverage_info)

  bbcov2lcov_binary = GetExecutableName(
      os.path.join(options.dynamorio_dir, 'tools', 'bin32', 'bbcov2lcov'))
  cmd = [
      bbcov2lcov_binary,
      '--dir', dynamorio_log_dir,
      '--output', coverage_info]
  RunCmd(cmd)

  # Assert coverage.info file exist
  if not os.path.isfile(coverage_info):
    print 'Failed to create coverage.info file.'
    return 1

  # Upload coverage file.
  cov_dir = options.test_to_upload.replace('_', '') + COVERAGE_DIR_POSTFIX
  dest = os.path.join(options.www_dir,
                      options.platform, options.build_id, cov_dir)
  dest = os.path.normpath(dest)
  if chromium_utils.IsWindows():
    print ('chromium_utils.CopyFileToDir(%s, %s)' %
           (coverage_info, dest))
    chromium_utils.MaybeMakeDirectory(dest)
    chromium_utils.CopyFileToDir(coverage_info, dest)
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    print 'SshCopyFiles(%s, %s, %s)' % (coverage_info, options.host, dest)
    chromium_utils.SshMakeDirectory(options.host, dest)
    chromium_utils.MakeWorldReadable(coverage_info)
    chromium_utils.SshCopyFiles(coverage_info, options.host, dest)
    os.unlink(coverage_info)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)
  return 0


def main():
  option_parser = optparse.OptionParser()

  # Required options:
  option_parser.add_option('--post-process', action='store_true',
                           help='Prepare dynamorio before running tests.')
  option_parser.add_option('--pre-process', action='store_true',
                           help='Process coverage after running tests.')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--build-id',
                           help='The build number of the tested build.')
  option_parser.add_option('--target',
                           help='Target directory.')
  option_parser.add_option('--platform',
                           help='Coverage subdir.')
  option_parser.add_option('--dynamorio-dir',
                           help='Path to dynamorio binary.')
  option_parser.add_option('--test-to-upload',
                           help='Test name.')

  chromium_utils.AddPropertiesOptions(option_parser)
  options, _ = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  fp = options.factory_properties
  options.browser_shard_index = fp.get('browser_shard_index')
  options.sharded_tests = fp.get('sharded_tests')
  options.host = fp.get('host')
  options.www_dir = fp.get('www-dir')
  del options.factory_properties
  del options.build_properties

  if options.pre_process:
    return PreProcess(options)
  elif options.post_process:
    return CreateCoverageFileAndUpload(options)
  else:
    print 'No valid options provided.'
    return 1


if '__main__' == __name__:
  sys.exit(main())
