#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive an Android build.

  This script is used for Debug and Release builds.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., <clankium>/src).

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import subprocess
import sys

from common import chromium_utils


def archive_build(target='Debug', name='archive.zip', location='out',
                  files=None, ignore_subfolder_names=False):
  out_dir = 'out'
  target_dir = os.path.join(out_dir, target)
  zip_file = os.path.join(location, name)
  expanded_files = []
  if files:
    for f in files:
      expanded_files.append(os.path.join(target_dir, f))
  else:
    expanded_files = [target_dir]

  saved_dir = os.getcwd()
  os.chdir(os.path.dirname(os.path.join(saved_dir, out_dir)))
  # Delete the zip file so we don't accidentally add to an existing archive.
  chromium_utils.RemoveFile(zip_file)
  zip_args = '-yr1'
  if ignore_subfolder_names:
    zip_args += 'j'
  command = ['zip', zip_args, zip_file]
  command.extend(expanded_files)
  subprocess.call(' '.join(command), shell=True)
  os.chdir(saved_dir)


def main(argv):
  option_parser = optparse.OptionParser()

  option_parser.add_option('--target', default='Debug',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('--name', default='archive.zip',
                           help='name of archive')
  option_parser.add_option('--location', default='out',
                           help='location to store archive in')
  option_parser.add_option('--files',
                           help='list of files to include - can be file paths '
                                'or globs')
  option_parser.add_option('--ignore-subfolder-names',
                           dest='ignore_subfolder_names',
                           action='store_true', default=False,
                           help='archive files without folder structure')
  options, args = option_parser.parse_args()
  if args:
    raise Exception('Unknown arguments: %s' % args)

  if options.files:
    options.files = options.files.split(',')
  return archive_build(target=options.target, name=options.name,
                       location=options.location, files=options.files,
                       ignore_subfolder_names=options.ignore_subfolder_names)


if '__main__' == __name__:
  sys.exit(main(None))
