#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to download/update the NaCl SDK, executed by buildbot.

When this is run, the current directory (cwd) should be the outer build
directory (e.g., chrome-release/build/). The required pepper bundle will be
requested and copied to nacl_sdk/pepper_current.
"""

from common import chromium_utils
chromium_utils.AddThirdPartyLibToPath('requests_1_2_3')

import hashlib
import optparse
import os
import shutil
import sys

import requests # pylint: disable=F0401

NACL_SDK_UPDATE_HOST = 'https://storage.googleapis.com'
NACL_SDK_UPDATE_PATH = '/nativeclient-mirror/nacl/nacl_sdk/nacl_sdk.zip'
NACL_SDK_UPDATE_URL = NACL_SDK_UPDATE_HOST + NACL_SDK_UPDATE_PATH
NACL_TOOL = os.path.join('nacl_sdk', 'naclsdk')
CURRENT_PEPPER_BUNDLE = os.path.join('nacl_sdk', 'pepper_current')


def Retrieve(response, file_name):
  """Downloads a file from a response to local destination 'file_name'."""
  with open(file_name, 'wb') as f:
    for b in response.iter_content(8192):
      if not b:
        break
      f.write(b)


def GetRevisionName(revision_list_output, pepper_channel):
  """Get pepper revision that matches the channel (stable, beta, etc)."""
  for line in revision_list_output.splitlines():
    line_chunks = line.split(' ')
    if (line_chunks[-1] == '(%s)' % pepper_channel
        and line_chunks[-2].startswith('pepper_')):
      return line_chunks[-2]
  raise Exception('Pepper channel %s not found.' % pepper_channel)


def GetFileHash(file_name):
  with open(file_name, 'rb') as f:
    return hashlib.sha256(f.read()).hexdigest()


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--pepper-channel', default='stable',
      help='Pepper channel (stable|beta|canary)')
  options, _ = option_parser.parse_args()

  work_dir = os.path.abspath('.')

  print 'Locating NaCl SDK update script at %s' % NACL_SDK_UPDATE_URL
  file_name = NACL_SDK_UPDATE_URL.split('/')[-1]
  response = requests.get(NACL_SDK_UPDATE_URL, verify=True, stream=True)

  file_hash = None
  if os.path.exists(file_name):
    file_hash = GetFileHash(file_name)

  print 'Downloading: %s' % file_name
  Retrieve(response, file_name)

  # Only extract if file changed. Extraction overwrites the sdk tools and the
  # state about which pepper revisions are up to date.
  if file_hash != GetFileHash(file_name):
    print 'Unzipping %s into %s' % (file_name, work_dir)
    chromium_utils.ExtractZip(file_name, work_dir, verbose=True)
  else:
    print 'Existing %s is up to date.' % file_name

  print 'Listing available pepper bundles:'
  output = chromium_utils.GetCommandOutput([NACL_TOOL, 'list'])
  print output
  pepper_rev = GetRevisionName(output, options.pepper_channel)

  print 'Updating pepper bundle %s' % pepper_rev
  cmd = [NACL_TOOL, 'update', pepper_rev, '--force']
  result = chromium_utils.RunCommand(cmd)

  if os.path.exists(CURRENT_PEPPER_BUNDLE):
    print 'Removing current pepper bundle %s' % CURRENT_PEPPER_BUNDLE
    shutil.rmtree(CURRENT_PEPPER_BUNDLE)

  pepper_rev_dir = os.path.join('nacl_sdk', pepper_rev)

  print 'Copying pepper bundle %s to current' % pepper_rev
  shutil.copytree(pepper_rev_dir, CURRENT_PEPPER_BUNDLE, symlinks=True)

  return result


if '__main__' == __name__:
  sys.exit(main())
