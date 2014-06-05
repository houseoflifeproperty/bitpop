#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Upload buildbot logfiles to google storage."""

import datetime
import glob
import os
import socket
import subprocess

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M')
HOSTNAME = socket.getfqdn().split('.', 1)[0]
BUILD_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir))


def GSUtilCopy(from_path, to_path, ignore_missing):
  """Upload a file to Google Storage."""
  if not os.path.exists(from_path):
    return int(not ignore_missing)
  # -z <ext> instructs gsutil to gzip files with that extension
  # and add 'Content-Encoding: gzip' to header.
  # gsutil determines file extension by looking a last segment
  # after spliting path on '.'.
  return subprocess.call([
      os.path.join(BUILD_DIR, 'third_party', 'gsutil', 'gsutil'),
      'cp', '-z', from_path.split('.')[-1], from_path,
      'gs://chromium-logs/%s/%s/%s' % (HOSTNAME, TIMESTAMP, to_path)])


def main():
  returncode = 0
  # See also: crbug.com/177922
  lkgr_base = os.path.join(BUILD_DIR, 'scripts', 'tools', 'lkgr_')
  returncode |= GSUtilCopy(lkgr_base + 'finder.log', 'lkgr.log', True)
  returncode |= GSUtilCopy(lkgr_base + 'build_data.json',
                           'lkgr_build_data.json', True)
  for logpath in glob.glob(
      os.path.join(BUILD_DIR, 'masters', '*', 'actions.log')):
    master = logpath.split(os.sep)[-2]
    if master.startswith('master.'):
      master = master[7:]
    returncode |= GSUtilCopy(logpath, '%s-actions.log' % master, False)
  return returncode


if __name__ == '__main__':
  exit(main())
