#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module for downloading files from Google Storage."""

import distutils.version
import optparse
import time

from slave import slave_utils


_POLL_INTERVAL_DEFAULT = 60 * 15  # 15 minutes
_TIMEOUT_DEFAULT = 60 * 60 * 2  # 2 hours


def DownloadLatestFile(base_url, partial_name, dst):
  """Get the latest archived object with the given base url and partial name.

  Args:
    base_url: Base Google Storage archive URL (gs://...) containing the build.
    partial_name: Partial name of the archive file to download.
    dst: Destination file/directory where the file will be downloaded.

  Raises:
    Exception: If unable to find or download a file.
  """
  base_url_glob = '%s/**' % base_url.rstrip('/')
  result = slave_utils.GSUtilListBucket(base_url_glob, ['-l'])

  if not result or result[0]:
    raise Exception('Could not find any archived files.')

  files = [b.split()[2] for b in result[1].split('\n')
           if partial_name in b]

  if not files:
    raise Exception('Could not find any matching files.')

  files = [distutils.version.LooseVersion(x) for x in files]
  newest_file = str(max(files))
  slave_utils.GSUtilDownloadFile(newest_file, dst)


def DownloadFileWithPolling(url, dst,
                            poll_interval=_POLL_INTERVAL_DEFAULT,
                            timeout=_TIMEOUT_DEFAULT):
  """Download the archived file with given |url|.

  If not found, keep trying at |poll_interval| until we reach |timeout|.

  Args:
    url: Google Storage URL (gs://...).
    dst: Destination file/directory where the file will be downloaded.
    poll_interval: Polling interval in seconds.
    timeout: Timeout in seconds.

  Raises:
    Exception: If there is a timeout.
  """
  start_time = time.time()
  time_passed = 0
  while time_passed < timeout:
    if not slave_utils.GSUtilDownloadFile(url, dst):
      return
    print 'Retrying in %d seconds...' % poll_interval
    time.sleep(poll_interval)
    time_passed = time.time() - start_time
  raise Exception('Timed out trying to download %s' % url)


def main():
  desc = ('There are 2 modes of downloading a file from Google Storage.\n'
          'If --poll is specified, poll Google Storage for the exact |url|\n'
          'at regular intervals until success or timeout.\n'
          'Otherwise, download the file with the given base URL and partial\n'
          'name. If there are multiple matching files, the newest is\n'
          'downloaded assuming the full URL follows a loose versioning format.'
         )
  parser = optparse.OptionParser(description=desc)

  parser.add_option('--url',
                    help='Google Storage URL (gs://...).')
  parser.add_option('--partial-name',
                    help='Partial name of the file to download.')
  parser.add_option('--dst', help='Path to the destination file/directory.')
  parser.add_option('--poll', action='store_true',
                    help='If specified poll for the exact url.')
  parser.add_option('--poll-interval', type=int, default=_POLL_INTERVAL_DEFAULT,
                    help='Poll interval in seconds [default: %default].')
  parser.add_option('--timeout', type=int, default=_TIMEOUT_DEFAULT,
                    help='Timeout in seconds [default: %default].')
  (options, args) = parser.parse_args()

  if args:
    parser.error('Unknown arguments: %s.' % args)

  if not (options.url and options.dst):
    parser.error('Missing one or more required arguments.')

  if options.poll:
    DownloadFileWithPolling(url=options.url,
                            dst=options.dst,
                            poll_interval=options.poll_interval,
                            timeout=options.timeout)
  else:
    if not options.partial_name:
      parser.error('Missing --partial_name.')

    DownloadLatestFile(base_url=options.url,
                       partial_name=options.partial_name,
                       dst=options.dst)


if __name__ == '__main__':
  main()
