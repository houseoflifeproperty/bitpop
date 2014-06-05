#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Apply a Subversion patch to the checkout.

This script can optionally pass the patch contents through an external filter
script to alter the contents.
As this script involves multiple subprocesses, the exit code of this script is a
result of the different subprocess exit codes. Each failing subprocess will get
its exit code printed to stdout and add a unique number to the script's combined
exit code (in order to make debugging easier).
"""

import optparse
import subprocess
import sys


SVN_CAT_FAILED = 1 << 0
FILTERING_FAILED = 1 << 1
PATCH_FAILED = 1 << 2


def main():
  parser = optparse.OptionParser()
  parser.add_option('-p', '--patch-url',
                    help='The SVN URL to download the patch from.')
  parser.add_option('-r', '--root-dir',
                    help='The root dir in which to apply patch.')
  parser.add_option('', '--filter-script',
                    help=('Path to a Python script to be used to manipulate '
                          'the contents of the patch. One example could be to '
                          'remove parts of the patch matching certain file '
                          'paths. The script must use stdin for input and '
                          'stdout for output. To pass flags to the script, '
                          'use: -- --flag1 --flag2'))
  parser.add_option('', '--strip-level', type='int', default=0,
                    help=('The number of path components to be stripped from '
                          'the filenames in the patch. Default: %default.'))

  options, args = parser.parse_args()
  if args and not options.filter_script:
    parser.error('Unused args: %s' % args)

  if not (options.patch_url and options.root_dir):
    parser.error('A patch URL and root directory should be specified.')

  svn_cat = subprocess.Popen(['svn', 'cat', options.patch_url],
                             stdout=subprocess.PIPE)
  patch_input = svn_cat.stdout
  filtering = None
  if options.filter_script:
    extra_args = args or []
    filtering = subprocess.Popen([sys.executable, options.filter_script] +
                                 extra_args,
                                 stdin=svn_cat.stdout, stdout=subprocess.PIPE,
                                 stderr=sys.stdout)
    patch_input = filtering.stdout
  patch = subprocess.Popen(['patch', '-t', '-p', str(options.strip_level),
                            '-d', options.root_dir],
                           stdin=patch_input)

  # Ensure we wait for the subprocesses to finish their execution and that we
  # check all their exit codes properly.
  procs = [('svn cat', svn_cat, SVN_CAT_FAILED)]
  if filtering:
    procs.append(('filtering', filtering, FILTERING_FAILED))
  procs.append(('patch', patch, PATCH_FAILED))
  patch.communicate()

  exit_code = 0
  for name, proc, fail_code in procs:
    proc.wait()
    if proc.returncode != 0:
      print '%s subprocess failed. Exit code: %s' % (name, proc.returncode)
      exit_code += fail_code
  return exit_code


if __name__ == '__main__':
  sys.exit(main())
