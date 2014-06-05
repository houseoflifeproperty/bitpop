#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Extract the latest dynamorio build."""

import optparse
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
import urllib
import urllib2

from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def GetLatestRevision(url, platform):
  """Return the latest official build revision as a string (e.g. '1234').

  To be clear, this does NOT download the latest revision; it just
  gets the number.
  """
  platform_map = {
    'win32': 'windows',
    'linux': 'linux',
  }
  try:
    # List by last modified date.
    response = urllib2.urlopen(url)
  except urllib2.URLError:
    print '\nFailed to read from URL: ' + url
    return None

  html = response.read()
  revision_list = re.findall(r'%s-r(\d+)\.' % platform_map[platform], html)
  if revision_list:
    return revision_list[-1]
  else:
    return None


def GetBuildUrl(url, platform, revision):
  """Compute the url to download the build from.

  Args:
    options: options object as specified by parser below.
  """
  platform_to_archive = {
    'win32': 'dynamorio-windows-r%s.zip',
    'linux': 'dynamorio-linux-r%s.tar.gz',
  }
  archive_name = platform_to_archive[platform] % revision
  url = url.rstrip('/')
  url = '%s/%s' % (url, archive_name)
  return url


def real_main(options):
  """Download a build and extract.

  Extract to build\BuildDir\full-build-win32 and rename it to
  build\BuildDir\Target
  """
  target_build_output_dir = os.path.join(options.build_dir, options.target)
  platform = chromium_utils.PlatformName()

  revision = options.revision
  if not revision:
    revision = GetLatestRevision(options.build_url, platform)
    if not revision:
      print 'Failed to get revision number.'
      return slave_utils.ERROR_EXIT_CODE

  archive_url = GetBuildUrl(options.build_url, platform, revision)
  archive_name = 'dynamorio.' + os.path.basename(archive_url).split('.', 1)[1]

  temp_dir = tempfile.mkdtemp()
  try:
    # We try to download and extract 3 times.
    for tries in range(1, 4):
      print 'Try %d: Fetching build from %s' % (tries, archive_url)

      failure = False
      try:
        print '%s/%s' % (archive_url, archive_name)
        urllib.urlretrieve(archive_url, archive_name)
        print '\nDownload complete'
      except IOError:
        print '\nFailed to download build'
        failure = True
        if options.halt_on_missing_build:
          return slave_utils.ERROR_EXIT_CODE
      if failure:
        continue

      print 'Extracting build %s to %s...' % (archive_name, options.build_dir)
      try:
        chromium_utils.RemoveDirectory(target_build_output_dir)
        chromium_utils.ExtractZip(archive_name, temp_dir)

        # Look for the top level directory from extracted build.
        entries = os.listdir(temp_dir)
        output_dir = temp_dir
        if (len(entries) == 1 and
            os.path.isdir(os.path.join(output_dir, entries[0]))):
          output_dir = os.path.join(output_dir, entries[0])

        print 'Moving build from %s to %s' % (output_dir,
                                              target_build_output_dir)
        shutil.move(output_dir, target_build_output_dir)
      except (OSError, IOError, chromium_utils.ExternalError):
        print 'Failed to extract the build.'
        # Print out the traceback in a nice format
        traceback.print_exc()
        # Try again...
        time.sleep(3)
        continue
      return 0
  finally:
    chromium_utils.RemoveDirectory(temp_dir)

  # If we get here, that means that it failed 3 times. We return a failure.
  return slave_utils.ERROR_EXIT_CODE


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option('--target',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--build-url',
                           help='url where to find the build to extract')
  option_parser.add_option('--revision',
                           help='Revision number to download.')
  option_parser.add_option('--halt-on-missing-build',
                           help='Halt on missing build.')
  chromium_utils.AddPropertiesOptions(option_parser)

  options, args = option_parser.parse_args()
  if args:
    print 'Unknown options: %s' % args
    return 1

  options.build_dir = build_directory.GetBuildOutputDirectory()
  options.build_dir = os.path.abspath(options.build_dir)

  options.build_url = (options.build_url or
                       options.factory_properties.get('build_url'))

  del options.factory_properties
  del options.build_properties

  return real_main(options)


if '__main__' == __name__:
  sys.exit(main())
