#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive an arbitrary file, executed by a buildbot slave.

  For a list of command-line options, call this script with '--help'.
"""

import optparse
import os
import shutil
import sys

from common import chromium_utils
import config


def UploadFile(src, dst, force_ssh=False):
  www_base = config.Archive.www_dir_base
  full_dst = os.path.join(www_base, dst)
  dst_dir = os.path.dirname(full_dst)
  if chromium_utils.IsWindows() and not force_ssh:
    print 'copying (%s) to (%s)' % (src, full_dst)
    chromium_utils.MaybeMakeDirectory(dst_dir)
    shutil.copyfile(src, full_dst)
    print 'done.'
  else:
    host = config.Archive.archive_host
    print 'copying (%s) to (%s) on (%s)' % (src, full_dst, host)
    chromium_utils.SshMakeDirectory(host, dst_dir)
    chromium_utils.SshCopyFiles(src, host, full_dst)
    print 'done.'


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--force-ssh', action='store_true',
      default=False, help='use ssh even on windows')
  option_parser.add_option('', '--target',
      help='destination to store result')
  option_parser.add_option('', '--source',
      help='file to send')

  options, args = option_parser.parse_args()
  if args:
    option_parser.error('No args supported')
  if not options.source:
    option_parser.error('No source specified')
  if not options.target:
    option_parser.error('No target specified')

  UploadFile(options.source, options.target,
             force_ssh=options.force_ssh)
  return 0


if '__main__' == __name__:
  sys.exit(main())
