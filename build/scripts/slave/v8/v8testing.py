#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the v8 tests.

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import sys

from common import chromium_utils

def main():
  if sys.platform in ('win32', 'cygwin'):
    default_platform = 'win'
    outdir = 'build'
  elif sys.platform.startswith('darwin'):
    default_platform = 'mac'
    outdir = 'xcodebuild'
  elif sys.platform == 'linux2':
    default_platform = 'linux'
    outdir = 'out'
  else:
    default_platform = None

  option_parser = optparse.OptionParser()

  option_parser.add_option('', '--testname',
                           default=None,
                           help='The test to run'
                                '[default: %default]')
  option_parser.add_option('', '--target',
                           default='Debug',
                           help='build target (Debug, Release) '
                                '[default: %default]')
  option_parser.add_option('', '--arch',
                           default='ia32',
                           help='Architecture (ia32, x64, arm) '
                                '[default: ia32]')
  option_parser.add_option('', '--platform',
                           default=default_platform,
                           help='specify platform [default: %%default]')
  option_parser.add_option('', '--shard_count',
                           default=1,
                           help='Specify shard count [default: %%default]')
  option_parser.add_option('', '--shard_run',
                           default=1,
                           help='Specify shard count [default: %%default]')
  option_parser.add_option('--shell_flags',
                           default=None,
                           help="Specify shell flags passed tools/test.py")
  option_parser.add_option('--isolates',
                           default=None,
                           help="Run isolates tests")


  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Unsupported arguments: %s' % args)

  simultaneous = '-j8'
  if options.platform in ('arm'):
    simultaneous = '-j1'

  os.environ['LD_LIBRARY_PATH'] = os.environ.get('PWD')

  if options.testname == 'leak':
    cmd = ['python', 'tools/test.py', '--no-build', '--mode',
           'debug', '--progress', 'verbose', '--timeout', '180',
           '--time', '-Snapshot=on', '--special-command',
           '"@ --nopreallocate-message-memory"',
           '--valgrind', 'mjsunit/leakcheck',
           'mjsunit/regress/regress-1134697', 'mjsunit/number-tostring-small']
  elif options.testname == 'presubmit':
    cmd = ['python', 'tools/presubmit.py']
  else:
    cmd = ['python', 'tools/test-wrapper-gypbuild.py',
           simultaneous,
           '--progress=verbose',
           '--buildbot',
           '--outdir=' + outdir,
           '--arch=' + options.arch,
           '--mode=' + options.target]
    if options.testname:
      cmd.extend([options.testname])
    if options.testname == 'test262':
      cmd.extend(['--download-data'])
    if options.testname == 'mozilla':
      # Mozilla tests requires a number of tests to timeout, set it a bit lower.
      if options.arch in ('arm', 'mipsel'):
        cmd.extend(['--timeout=180'])
      else:
        cmd.extend(['--timeout=120'])
    elif options.shell_flags and '--gc-interval' in options.shell_flags:
      # GC Stress testing takes much longer, set generous timeout.
      if options.arch in ('arm', 'mipsel'):
        cmd.extend(['--timeout=900'])
      else:
        cmd.extend(['--timeout=600'])
    else:
      if options.arch in ('arm', 'mipsel'):
        cmd.extend(['--timeout=600'])
      else:
        cmd.extend(['--timeout=200'])
    if options.isolates:
      cmd.extend(['--isolates'])
    if options.shell_flags:
      cmd.extend(["--special-command", options.shell_flags.replace("\"", "")])



  if options.shard_count > 1:
    cmd.extend(['--shard-count=%s' % options.shard_count,
                '--shard-run=%s' % options.shard_run])

  return chromium_utils.RunCommand(cmd)


if __name__ == '__main__':
  sys.exit(main())
