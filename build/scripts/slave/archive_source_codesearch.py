#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to create tarball from chromium source code

This script is created instead of just running commands from recipe because
recipe does not support pipe."""


import optparse
import os
import subprocess
import sys
import time

def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('-f', '--file', dest='filename',
                          help='archive file name', metavar='FILE')
  options, dirs = option_parser.parse_args()
  filename = options.filename or 'chromium.tar.bz2'

  for d in dirs:
    if not os.path.exists(d):
      raise Exception('ERROR: no %s directory to package, exiting' % d)

  print '%s: Creating tar file %s...' % (time.strftime('%X'), filename)
  find_command = ['find'] + dirs + ['-type', 'f', '-size', '-4M',
                  # The only files under src/out we want to package up
                  # are index files and generated sources.
                  '(', '-regex', '^src/out/.*index$', '-o',
                       '-regex', '^src/out/[^/]*/gen/.*', '-o',
                       '!', '-regex', '^src/out/.*', ')',
                  # Exclude all .svn directories, the native client toolchain
                  # and the llvm build directory, and perf/data files.
                  '-a', '!', '-regex', r'.*\.svn.*',
                  '-a', '!', '-regex', r'.*\.git.*',
                  '-a', '!', '-regex', '^src/data/.*',
                  '-a', '!', '-regex', '^src/native_client/toolchain/.*',
                  '-a', '!', '-regex', '^src/third_party/llvm-build/.*',
                  '-a', '!', '-regex',
                    '^src/chrome/tools/test/reference_build/.*',
                  '-a', '!', '-regex', '^tools/perf/data/.*']

  find_proc = subprocess.Popen(find_command, stdout=subprocess.PIPE)
  tar_proc = subprocess.Popen(['tar', '-T-', '-cjvf', filename],
                              stdin=find_proc.stdout)
  find_proc.stdout.close()
  find_proc.wait()
  tar_proc.communicate()
  if tar_proc.returncode == 0 and find_proc.returncode == 0:
    return 0
  return 1

if '__main__' == __name__:
  sys.exit(main())
