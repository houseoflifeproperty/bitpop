#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A simple trampoline to isolate.py in the src/ directory.

Intercepts the --build-dir and --target flags and inserts them into the
--isolated flag. isolate.py doesn't understand --build-dir and --target.
"""

import os
import sys
from slave import build_directory
from common import chromium_utils

from slave.swarming import swarming_utils


def InterceptFlag(flag, args):
  new_args, i, flag_value = [], 0, None
  while i < len(args):
    if args[i] == flag:
      flag_value = args[i + 1]
      i += 1
    elif args[i].startswith(flag + '='):
      flag_value = args[i][len(flag + '='):]
    else:
      new_args.append(args[i])
    i += 1
  return flag_value, new_args


def AdjustIsolatedFlag(args, base_dir):
  """Prepends base_dir to an argument to --isolated."""
  # Note: The position of --isolated in args matters (it has to be in front
  # of a '--'), so don't do call InterceptFlag('--isolated') and then append
  # the transformed result to the end of args.
  for i in range(len(args)):
    if args[i] == '--isolated':
      args[i + 1] = os.path.join(base_dir, args[i + 1])
    elif args[i].startswith('--isolated='):
      p = args[i][len('--isolated='):]
      args[i] = '--isolated=' + os.path.join(base_dir, p)


def main():
  client = swarming_utils.find_client(os.getcwd())
  if not client:
    print >> sys.stderr, 'Failed to find swarm(ing)_client'
    return 1
  # Replace the 'isolate_shim.py' wrapper with 'isolate.py'.
  args = [sys.executable, os.path.join(client, 'isolate.py')] + sys.argv[1:]
  build_dir, args = InterceptFlag('--build-dir', args)
  target, args = InterceptFlag('--target', args)

  if build_dir:
    assert target
    build_dir = build_directory.GetBuildOutputDirectory()
    AdjustIsolatedFlag(args, os.path.join(build_dir, target))

  return chromium_utils.RunCommand(args)


if '__main__' == __name__:
  sys.exit(main())
