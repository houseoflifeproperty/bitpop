#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Downloads and unpacks an O3D test archive.

Usage:
  unpack_test_archive.py [--url archive_url] [--builder <builder_name>]

Command Arguments:
  archive_url:  the url of a zipped O3D test archive.
  builder_name:  the name of an O3D builder.
"""


import optparse
import os
import shutil
import sys
import urllib
import urlparse

from common import chromium_utils as utils

import config

if utils.IsWindows():
  AUTO_PATH = 'C:\\auto'

elif utils.IsMac():
  AUTO_PATH = '/Users/testing/auto'

else:
  AUTO_PATH = '/home/testing/auto'


O3D_PATH = os.path.join(AUTO_PATH, 'o3d')
SCRIPTS_PATH = os.path.join(AUTO_PATH, 'scripts')
O3D_SRC_AUTO_PATH = os.path.join(O3D_PATH, 'o3d', 'tests', 'lab')
ARCHIVE_BASE_URL = ('http://' + config.Archive.archive_host +
                    '/buildbot/snapshots/o3d/test_packages/')

class StagingError(Exception): pass


def DownloadTestArchive(archive_url):
  """Download test archive from webserver.

  Args:
    archive_url: url of the archive to be downloaded
  Returns:
    path to local test archive
  """
  if archive_url.startswith('file:'):
    # File already on disk.
    local_path = urlparse.urlparse(archive_url)[2]
  else:
    # Download test archive from url.
    local_path = os.path.join(AUTO_PATH, 'o3d.zip')
    print 'Downloading', archive_url, 'to', local_path
    urllib.urlretrieve(archive_url, local_path)

  return local_path


def unpack(options):
  if not options.url and not options.builder:
    raise StagingError('Either a test url or builder name is required.')

  # Remove existing test archive.
  if os.path.exists(AUTO_PATH):
    print 'Removing existing directory at', AUTO_PATH
    shutil.rmtree(AUTO_PATH)

  os.mkdir(AUTO_PATH)

  # Download archive.
  if options.url:
    url = options.url
  else:
    # Find latest archive.
    branch = 'o3d'
    latest_path = branch + '/latest_' + options.builder
    latest_url = ARCHIVE_BASE_URL + latest_path

    local_latest = os.path.join(AUTO_PATH, 'latest')
    print 'Downloading latest file from', latest_url
    urllib.urlretrieve(latest_url, local_latest)

    latest_file = file(local_latest, 'r')
    url = ARCHIVE_BASE_URL + branch + '/' + latest_file.readline()
  try:
    local_archive_path = DownloadTestArchive(url)
  except IOError:
    print 'IOError while downloading test archive from', url
    return 2

  # Unzip archive.
  output_dir = os.path.normpath(os.path.join(O3D_PATH, '..'))
  print 'Extracting test archive to', output_dir
  utils.ExtractZip(local_archive_path, output_dir, False)

  # Copy archive's automation scripts into auto directory.
  print 'Copying automation scripts from', O3D_SRC_AUTO_PATH, 'to', SCRIPTS_PATH
  shutil.copytree(O3D_SRC_AUTO_PATH, SCRIPTS_PATH)
  return 0


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option('', '--url',
      help='url of test archive')
  option_parser.add_option('', '--builder',
      help='name of builder to grab archive from')

  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Unsupported arguments: %s' % args)
  return unpack(options)


if '__main__' == __name__:
  sys.exit(main())
