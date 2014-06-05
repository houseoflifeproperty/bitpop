#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Runs a command with PYTHONPATH set up for the Chromium build setup.

This is helpful for running scripts locally on a development machine.

Try `scripts/common/runit.py python`
or  (in scripts/slave): `../common/runit.py runtest.py --help`
"""

import optparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BUILD_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

USAGE = '%s [options] <command to run>' % os.path.basename(sys.argv[0])

# These third_party libs interfere with other imports in PYTHONPATH and should
# be put last. Please file bugs to clean up each entry here.
troublemakers = [
    'cbuildbot_chromite',  # crbug.com/321266
]


def add_build_paths(path_list):
  """Prepend required paths for build system to the provided path_list.

  path_list is modified in-place. It can be sys.path or something else.
  No paths are added twice.
  """

  # First build the list of required paths
  build_paths = []

  third_party = os.path.join(BUILD_DIR, 'third_party')

  # Put troublemakers first, which when prepended will put them last.
  keyfunc = lambda x: (1 if x not in troublemakers else -troublemakers.index(x))
  for d in sorted(os.listdir(third_party), key=keyfunc):
    full = os.path.join(third_party, d)
    if os.path.isdir(full):
      build_paths.append(full)

  build_paths.append(os.path.join(BUILD_DIR, 'scripts'))
  build_paths.append(third_party)
  build_paths.append(os.path.join(BUILD_DIR, 'site_config'))
  build_paths.append(os.path.join(BUILD_DIR,
                                  '..', 'build_internal', 'site_config'))
  build_paths.append(os.path.join(BUILD_DIR,
                                  '..', 'build_internal', 'scripts', 'master'))

  # build_paths now contains all the required paths, in *reverse order*
  # of priority.

  # Prepend the list of paths to path_list. We take care of possible
  # duplicates here.
  for path in build_paths:
    if path not in path_list:
      path_list.insert(0, path)


def main():
  option_parser = optparse.OptionParser(usage=USAGE)
  option_parser.add_option('-s', '--show-path', action='store_true',
                           help='display new PYTHONPATH before running command')
  option_parser.disable_interspersed_args()
  options, args = option_parser.parse_args()
  if not args:
    option_parser.error('Must provide a command to run.')

  path = os.environ.get('PYTHONPATH', '').split(os.pathsep)
  add_build_paths(path)
  os.environ['PYTHONPATH'] = os.pathsep.join(path)

  if options.show_path:
    print 'Set PYTHONPATH: %s' % os.environ['PYTHONPATH']

  # Use subprocess instead of execv because otherwise windows destroys quoting.
  p = subprocess.Popen(args)
  p.wait()
  return p.returncode


if __name__ == '__main__':
  sys.exit(main())
