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
import shutil
import subprocess
import sys


def main_common(cov_file, cmdline):
  """Common main() routine.

  Args:
    cov_file: the coverage file we will be working with.
    cmdline: the command line to execute.
  """
  # Print some details which may help debugging.
  try:
    print os.stat(cov_file)
  except (OSError, IOError):
    print 'Stat of %s failed (file not found?)' % cov_file

  # Croc.
  print 'Running croc:', cmdline
  result = subprocess.call(cmdline)

  # Move aside the coverage file so a deps check always rebuilds it.
  saved_name = cov_file + '.old'
  print 'Moving %s to %s (if possible)' % (cov_file, saved_name)
  if os.path.exists(saved_name):
    os.remove(saved_name)
  if os.path.exists(cov_file):
    shutil.move(cov_file, saved_name)

  return result


def main_mac(options, args):
  """Print appropriate size information about built Mac targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.
  """
  target_dir = os.path.join(os.path.dirname(options.build_dir),
                            'xcodebuild', options.target)
  cov_file = os.path.join(target_dir, 'coverage.info')

  cmdline = [
      sys.executable,
      'src/tools/code_coverage/croc.py',
      '-c', 'src/build/common.croc',
      '-c', 'src/build/mac/chrome_mac.croc',
      '-i', cov_file,
      '-r', os.getcwd(),
      '--tree',
      '--html', os.path.join(target_dir, 'coverage_croc_html'),
      ]

  return main_common(cov_file, cmdline)


def main_linux(options, args):
  """Print appropriate size information about built Linux targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.

  Assumes make, not scons.
  """
  target_dir = os.path.join(os.path.dirname(options.build_dir),
                            'out', options.target)
  if os.path.exists(os.path.join(target_dir, 'total_coverage')):
    print 'total_coverage directory exists'
    total_cov_file = os.path.join(target_dir,
                                  'total_coverage',
                                  'coverage.info')
    cmdline = [
        sys.executable,
        'src/tools/code_coverage/croc.py',
        '-c', 'src/build/common.croc',
        '-c', 'src/build/linux/chrome_linux.croc',
        '-i', total_cov_file,
        '-r', os.getcwd(),
        '--tree',
        '--html',
        os.path.join(target_dir, 'total_coverage', 'coverage_croc_html'),
        ]
    result = main_common(total_cov_file, cmdline)

  if os.path.exists(os.path.join(target_dir, 'unittests_coverage')):
    print 'unittests_coverage directory exists'
    unittests_cov_file = os.path.join(target_dir,
                                      'unittests_coverage',
                                      'coverage.info')
    cmdline = [
        sys.executable,
        'src/tools/code_coverage/croc.py',
        '-c', 'src/build/common.croc',
        '-c', 'src/build/linux/chrome_linux.croc',
        '-i', unittests_cov_file,
        '-r', os.getcwd(),
        '--tree',
        '--html',
        os.path.join(target_dir, 'unittests_coverage', 'coverage_croc_html'),
        ]
    unittests_result = main_common(unittests_cov_file, cmdline)

  if unittests_result != 0:
    result = unittests_result
  return result


def main_win(options, args):
  """Print appropriate size information about built Windows targets.

  Returns the first non-zero exit status of any command it executes,
  or zero on success.
  """
  target_dir = os.path.join(options.build_dir, options.target)
  cov_file = os.path.join(target_dir, 'coverage.info')

  cmdline = [
      sys.executable,
      'src/tools/code_coverage/croc.py',
      '-c', 'src/build/common.croc',
      '-c', 'src/build/win/chrome_win.croc',
      '-i', cov_file,
      '-r', os.getcwd(),
      '--tree',
      '--html', os.path.join(target_dir, 'coverage_croc_html'),
      ]

  return main_common(cov_file, cmdline)


def main():
  if sys.platform in ('win32', 'cygwin'):
    default_platform = 'win'
  elif sys.platform.startswith('darwin'):
    default_platform = 'mac'
  elif sys.platform == 'linux2':
    default_platform = 'linux'
  else:
    default_platform = None

  main_map = {
    'linux' : main_linux,
    'mac' : main_mac,
    'win' : main_win,
  }
  platforms = sorted(main_map.keys())

  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--target',
                           default='Debug',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('', '--build-dir',
                           default='chrome',
                           metavar='DIR',
                           help='directory in which build was run '
                                '[default: %default]')
  option_parser.add_option('', '--platform',
                           default=default_platform,
                           help='specify platform (%s) [default: %%default]'
                                % ', '.join(platforms))

  options, args = option_parser.parse_args()

  real_main = main_map.get(options.platform)
  if not real_main:
    if options.platform is None:
      sys.stderr.write('Unsupported sys.platform %s.\n' % repr(sys.platform))
    else:
      sys.stderr.write('Unknown platform %s.\n' % repr(options.platform))
    msg = 'Use the --platform= option to specify a supported platform:\n'
    sys.stderr.write(msg + '    ' + ' '.join(platforms) + '\n')
    return 2
  return real_main(options, args)


if '__main__' == __name__:
  sys.exit(main())
