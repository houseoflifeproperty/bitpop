#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import shutil
import sys
import tempfile
import urllib
import zipfile


def get_gae_sdk_version(gae_path):
  """Returns the installed GAE SDK version or None."""
  version_path = os.path.join(gae_path, 'VERSION')
  if os.path.isfile(version_path):
    values = dict(
        map(lambda x: x.strip(), l.split(':'))
        for l in open(version_path) if ':' in l)
    if 'release' in values:
      return values['release'].strip('"')


def get_latest_gae_sdk_url():
  """Returns the url to get the latest GAE SDK."""
  content = urllib.urlopen(
      'https://code.google.com/appengine/downloads.html').read()
  regexp = (
      r'(http\:\/\/googleappengine\.googlecode.com\/files\/'
      r'google_appengine_.+?\.zip)')
  m = re.search(regexp, content)
  url = m.group(1)
  # Upgrade to https
  return url.replace('http://', 'https://')


def install_latest_gae_sdk(root_path):
  gae_path = os.path.join(root_path, 'google_appengine')
  version = get_gae_sdk_version(gae_path)
  if version:
    print 'Found installed version %s' % version

  url = get_latest_gae_sdk_url()
  # Calculate the version from the url.
  new_version = re.search(r'appengine_(.+?).zip', url).group(1)
  print 'New version is %s' % new_version
  if version == new_version:
    return 0

  if os.path.isdir(gae_path):
    print 'Removing previous version'
    shutil.rmtree(gae_path)

  print 'Fetching %s' % url
  with tempfile.NamedTemporaryFile() as f:
    urllib.urlretrieve(url, f.name)
    # The path already contains 'google_appengine'
    print 'Extracting into %s' % root_path
    z = zipfile.ZipFile(f.name, 'r')
    try:
      z.extractall(root_path)
    finally:
      z.close()
  return 0


def main():
  base_path = os.path.dirname(os.path.abspath(__file__))
  return install_latest_gae_sdk(os.path.dirname(base_path))


if __name__ == '__main__':
  sys.exit(main())
