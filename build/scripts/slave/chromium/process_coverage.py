#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run croc to generate code coverage, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import re
import shutil
import subprocess
import sys

from common import chromium_utils
from slave import build_directory


COVERAGE_DIR_POSTFIX = '_coverage'
COVERAGE_INFO = 'coverage.info'


def RunCroc(cov_files, cmdline):
  """Common main() routine.

  Args:
    cov_files: the coverage file we will be working with.
    cmdline: the command line to execute.
  """
  # Print some details which may help debugging.
  for cov_file in cov_files:
    try:
      print os.stat(cov_file)
    except (OSError, IOError), e:
      print 'Stat of %s failed. %s' % (cov_file, e)

  # Croc.
  print 'Running croc:', cmdline
  result = subprocess.call(cmdline)

  # Move aside the coverage file so a deps check always rebuilds it.
  for cov_file in cov_files:
    saved_name = cov_file + '.old'
    print 'Moving %s to %s (if possible)' % (cov_file, saved_name)
    if os.path.exists(saved_name):
      os.remove(saved_name)
    if os.path.exists(cov_file):
      shutil.move(cov_file, saved_name)

  return result


def CrocCommand(platform, cov_files, html_dir):
  cmdline = [
    sys.executable,
    'src/tools/code_coverage/croc.py',
    '-c', 'src/build/common.croc',
    '-c', 'src/build/%s/chrome_%s.croc' % (platform, platform),
    '-r', os.getcwd(),
    '--tree',
    '--html', html_dir]
  for cov_file in cov_files:
    cmdline += ['-i', cov_file]
  return cmdline


def ReplaceCoveragePath(cov_file, build_dir):
  """Replace the coverage path to this system 'src' directory."""
  src_dir = chromium_utils.AbsoluteCanonicalPath(
      os.path.join(build_dir, '..'))
  src_dir = os.path.normpath(src_dir)

  input_file = open(cov_file)
  cov_lines = input_file.readlines()
  input_file.close()

  fhandler = open(cov_file, 'w')
  for line in cov_lines:
    line = re.sub(r'SF:.*[\\/]src[\\/]', 'SF:%s/' % src_dir, line, 1)
    line = line.replace('\\', '/')
    fhandler.write(line)
  fhandler.close()


def FetchCoverageFiles(options):
  """Fetch coverage files from www dir to be processed."""
  target_dir = os.path.join(options.build_dir, options.target)
  for test in options.tests:
    cov_dir = test.replace('_', '') + COVERAGE_DIR_POSTFIX
    output_path = os.path.join(target_dir, cov_dir)
    chromium_utils.MaybeMakeDirectory(output_path)
    cov_src = ('/%s/%s/%s/%s/' % (options.upload_dir, options.platform,
                                  options.build_id, cov_dir))
    if options.sharded_tests and test in options.sharded_tests:
      # Copy all Lvoc files.
      for shard_count in xrange(1, options.browser_total_shards + 1):
        src = cov_src + 'coverage_%s.info' % shard_count
        chromium_utils.CopyFileToDir(src, output_path)
    else:
      chromium_utils.CopyFileToDir(cov_src + COVERAGE_INFO, output_path)


def ProcessCoverage(options, args):
  """Print appropriate size information about built Windows targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.
  """
  # Fetch coverage from archive if we're running sharded tests.
  if options.browser_total_shards:
    FetchCoverageFiles(options)

  # Process total coverage.
  coverage_dirs = [x.replace('_', '') + COVERAGE_DIR_POSTFIX for x in
                   options.tests]
  target_dir = os.path.join(options.build_dir, options.target)
  cov_files = []
  for cov in coverage_dirs:
    cov_dir = os.path.join(target_dir, cov)
    if os.path.exists(cov_dir):
      print cov + ' directory exists.'
      for fname in os.listdir(cov_dir):
        if fname.endswith('.info'):
          cov_file = os.path.join(cov_dir, fname)
          cov_files.append(cov_file)
          ReplaceCoveragePath(cov_file, options.build_dir)

  if cov_files:
    total_coverage = os.path.join(target_dir, 'total_coverage')
    chromium_utils.MaybeMakeDirectory(total_coverage)
    html_dir = os.path.join(total_coverage, 'coverage_croc_html')
    cmdline = CrocCommand(options.platform, cov_files, html_dir)
    return RunCroc(cov_files, cmdline)
  else:
    print 'No coverage files found.'
    return 1


def main():
  if sys.platform in ('win32', 'cygwin'):
    default_platform = 'win'
  elif sys.platform.startswith('darwin'):
    default_platform = 'mac'
  elif sys.platform == 'linux2':
    default_platform = 'linux'
  else:
    default_platform = None

  platforms = ['linux', 'mac', 'win']

  option_parser = optparse.OptionParser()
  option_parser.add_option('--target',
                           default='Debug',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--platform',
                           default=default_platform,
                           help='specify platform (%s) [default: %%default]'
                                % ', '.join(platforms))
  option_parser.add_option('--build-id',
                           help='The build number of the tested build.')
  option_parser.add_option('--upload-dir',
                           help='Path coverage file was uploaded to.')

  chromium_utils.AddPropertiesOptions(option_parser)
  options, args = option_parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  fp = options.factory_properties
  options.tests = fp.get('tests')
  options.sharded_tests = fp.get('sharded_tests')
  options.browser_total_shards = fp.get('browser_total_shards')
  del options.factory_properties
  del options.build_properties

  if options.platform not in platforms:
    sys.stderr.write('Unsupported sys.platform %s.\n' % repr(sys.platform))
    msg = 'Use the --platform= option to specify a supported platform:\n'
    sys.stderr.write(msg + '    ' + ' '.join(platforms) + '\n')
    return 2
  return ProcessCoverage(options, args)


if '__main__' == __name__:
  sys.exit(main())
