#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# delete_old_files.py: Deletes files older than a certain date from a directory.

import optparse
import os
import sys
import time

DESCRIPTION = """Cleans a directory of any files that haven't been accessed
within the specified number of hours."""


def GetOldFiles(directory, time_in_seconds):
  """
  Gets all of the files in the given directory that haven't been accessed in the
  last time_in_seconds seconds.

  Args:
    directory: The directory to iterate through.
    time_in_seconds: The cut off time for a file being old.

  Returns:
    A list of all the old files in this directory and its subdirectories.
  """
  old_files = []
  # Store time as a variable so all files work with the same time.
  current_time = time.time()

  for (root, _, files) in os.walk(directory):
    for filename in files:
      file_path = os.path.join(root, filename)
      if (current_time - os.path.getatime(file_path)) > time_in_seconds:
        old_files.append(file_path)

  return old_files


def main():
  parser = optparse.OptionParser(
      usage='%prog [options]',
      description=DESCRIPTION)
  parser.add_option('-d', '--directory', help='The directory to clean.')
  parser.add_option('-t', '--time', type=int, default=1,
                    help='The number of hours a file must have been accessed '
                    'within to avoid deletion. Defaults to %default')
  parser.add_option('-f', '--force', action='store_true',
                    help='Used to indicate if the files should be deleted, '
                    'otherwise the list of files that would be deleted is just '
                    ' printed.')

  (options, args) = parser.parse_args()

  if args:
    parser.error('Unknown arguments given')
  if not options.directory:
    parser.error('Must specify a directory to clean.')
  if options.time < 0:
    parser.error('The specific time must be a positive number')

  # Convert the time from hours to seconds.
  time_in_seconds = options.time * 3600

  old_files = GetOldFiles(options.directory, time_in_seconds)

  if options.force:
    map(os.remove, old_files)
  else:
    if old_files:
      print '\n'.join(old_files)
    else:
      print 'No files found.'


if __name__ == '__main__':
  sys.exit(main())
