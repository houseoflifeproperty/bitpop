#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Get official or chromium build, executed by buildbot slaves for Chromebot.

This script will download Chrome build, test files, and breakpad symbol files
with option to extract.

If (--build) is omitted, latest build will be fetched.

Chromebot server bot will run:
  get_build_for_chromebot.py --platform=PLATFORM  --archive-url=ARCHIVE_URL

Chromebot client bot will run:
  get_build_for_chromebot.py --platform=PLATFORM --extract
    --build-url=BUILD_URL_ON_SERVER_BOT
"""

import httplib
import optparse
import os
import shutil
import sys
import tarfile
import tempfile
import urlparse
import urllib
import urllib2
import zipfile


def RemovePath(path):
  """Remove the given dir."""
  if os.path.isdir(path):
    shutil.rmtree(path)


def MoveFile(path, new_path):
  """Move all content in |path| to |new_path|.

  Create |new_path| if it doesn't exist.
  """
  if not os.path.isdir(new_path):
    os.makedirs(new_path)
  for root, dirnames, fnames in os.walk(path):
    for fname in fnames:
      shutil.move(os.path.join(root, fname), new_path)
    for dirname in dirnames:
      shutil.move(os.path.join(root, dirname), new_path)
  RemovePath(path)


def Extract(zip_file, dest):
  """Extract to |dest|.  Remove zip file and remove top level directory."""
  temppath = tempfile.mkdtemp()
  try:
    z = zipfile.ZipFile(zip_file)
    z.extractall(temppath)
    z.close()
  except zipfile.BadZipfile:
    t = tarfile.open(zip_file, 'r:bz2')
    t.extractall(temppath)
  os.remove(zip_file)

  # Remove the top level directory in the zip file.
  entries = os.listdir(temppath)
  if len(entries) == 1 and os.path.isdir(os.path.join(temppath, entries[0])):
    temppath = os.path.join(temppath, entries[0])
  MoveFile(temppath, dest)


def DoesURLExist(url):
  """Determines whether a resource exists at the given URL."""
  _, netloc, path, _, _, _ = urlparse.urlparse(url.replace(' ', '%20'))
  conn = httplib.HTTPConnection(netloc)
  try:
    conn.request('HEAD', path)
  except httplib.HTTPException:
    return False
  response = conn.getresponse()
  if response.status == 302:  # Redirect; follow it.
    return DoesURLExist(response.getheader('location'))
  return response.status == 200


class GetBuild(object):
  """Class for downloading the build."""

  def __init__(self, options):
    super(GetBuild, self).__init__()
    self._build_id = None
    self._archive_url = None
    self._chrome_zip_name = None
    self._chrome_zip_url = None
    self._options = options
    self._symbol_dir = None
    self._symbol_url = None
    self._symbol_name = None
    self._target_dir = None
    self._test_name = None
    self._test_url = None
    self._ffmpegsumo_name = None
    self._ffmpegsumo_url = None

    self._chromium_archive = ('http://commondatastorage.googleapis.com/'
                              'chromium-browser-snapshots/')

    # Mapping from platform to build file name for chromium archive.
    # .../PLATFORM/REVISION/
    self._urlmap = {
      'mac': {
        'chrome_zip': 'Mac/%s/chrome-mac.zip',
        'test': 'Mac/%s/chrome-mac.test/reliability_tests',
        'symbol': 'Mac/%s/chrome-mac-syms.zip',
        'lastchange': 'Mac/LAST_CHANGE',
        'ffmpegsumo': 'Mac/%s/chrome-mac.test/ffmpegsumo.so',
      },
      'win': {
        'chrome_zip': 'Win/%s/chrome-win32.zip',
        'test': 'Win/%s/chrome-win32.test/reliability_tests.exe',
        'symbol': 'Win/%s/chrome-win32-syms.zip',
        'lastchange': 'Win/LAST_CHANGE'
      },
      'linux': {
        'chrome_zip': 'Linux/%s/chrome-linux.zip',
        'test': 'Linux/%s/chrome-linux.test/reliability_tests',
        'symbol': 'Linux/%s/chrome-lucid32bit-syms.zip',
        'lastchange': 'Linux/LAST_CHANGE'
      },
      'linux64': {
        'chrome_zip': 'Linux_x64/%s/chrome-linux.zip',
        'test': 'Linux_x64/%s/chrome-linux.test/reliability_tests',
        'symbol': 'Linux_x64/%s/chrome-lucid64bit-syms.zip',
        'lastchange': 'Linux_x64/LAST_CHANGE'
      },
    }

  def GetLastChange(self, base_url):
    """Get the latest revision number from web file."""
    last_change_url = self.GetURL(base_url, 'lastchange')
    try:
      url_handler = urllib2.urlopen(last_change_url)
      latest = url_handler.read()
      return latest.strip()
    except IOError:
      print('Could not retrieve the latest revision.', last_change_url)
      return None

  def GetURL(self, base_url, file_type):
    """Get full url path to file.

    Args:
      file_type: String ('chrome_zip', 'test', 'symbol', 'lastchange').
    """
    url = base_url + self._urlmap[self._options.platform][file_type]
    if file_type == 'lastchange':
      return url
    return url % self._build_id

  def GetDownloadFileName(self, file_type):
    """Get file base name from |_urlmap|."""
    return os.path.basename(self._urlmap[self._options.platform][file_type])

  def ProcessArgs(self):
    """Make sure we have proper args; setup download and extracting paths."""
    if not self._options.platform in ('win', 'linux', 'linux64', 'mac'):
      print 'Unsupported platform.' % self._options.platform
      return False

    if self._options.build_url and not self._options.build_url.endswith('/'):
      self._options.build_url += '/'
    if (self._options.archive_url and
        not self._options.archive_url.endswith('/')):
      self._options.archive_url += '/'

    if self._options.archive_url:
      self._archive_url = self._options.archive_url
    elif not self._options.build_url:
      self._archive_url = self._chromium_archive

    # Get latest build if no |build| is provided.
    if not self._options.build and not self._options.build_url:
      self._build_id = self.GetLastChange(self._archive_url)
      if not self._build_id:
        print 'Failed to get the latest build.'
        return False

    self._target_dir = os.path.join(self._options.build_dir,
                                    self._options.target_dir)
    self._symbol_dir = os.path.join(self._options.build_dir, 'breakpad_syms')

    self._chrome_zip_name = self.GetDownloadFileName('chrome_zip')
    self._test_name = self.GetDownloadFileName('test')
    self._symbol_name = self.GetDownloadFileName('symbol')

    # Set download URLs.
    if self._archive_url:
      self._chrome_zip_url = self.GetURL(self._archive_url, 'chrome_zip')
      self._test_url = self.GetURL(self._archive_url, 'test')
      self._symbol_url = self.GetURL(self._archive_url, 'symbol')
    else:
      self._chrome_zip_url = self._options.build_url + self._chrome_zip_name
      self._test_url = self._options.build_url + self._test_name
      self._symbol_url = self._options.build_url + self._symbol_name

    if self._options.platform == 'mac':
      self._ffmpegsumo_name = self.GetDownloadFileName('ffmpegsumo')
      if self._archive_url:
        self._ffmpegsumo_url = self.GetURL(self._archive_url, 'ffmpegsumo')
      else:
        self._ffmpegsumo_url = self._options.build_url + self._ffmpegsumo_name

    return True

  def CleanUp(self):
    """Clean up current directory (e.g. delete prev downloads)."""
    print 'Cleaning these paths: '
    print self._target_dir, self._symbol_dir
    RemovePath(self._target_dir)
    RemovePath(self._symbol_dir)
    return True

  def DownloadAndExtractFiles(self):
    """Download and extract files."""
    if not DoesURLExist(self._chrome_zip_url):
      print 'URL does not exist : ' + self._chrome_zip_url
      return False

    os.makedirs(self._target_dir)
    os.chmod(self._target_dir, 0755)

    # Download and extract Chrome zip.
    print 'Downloading URL: ' + self._chrome_zip_url
    file_path = os.path.join(self._target_dir, self._chrome_zip_name)
    urllib.urlretrieve(self._chrome_zip_url, file_path)
    if self._options.extract:
      Extract(file_path, self._target_dir)

    # Download test file.
    print 'Downloading URL: ' + self._test_url
    file_path = os.path.join(self._target_dir, self._test_name)
    urllib.urlretrieve(self._test_url, file_path)

    # Download and extract breakpad symbols.
    print 'Downloading URL: ' + self._symbol_url
    file_path = os.path.join(self._target_dir, self._symbol_name)
    urllib.urlretrieve(self._symbol_url, file_path)
    if self._options.extract:
      Extract(file_path, self._symbol_dir)

    # Download ffmpegsumo.so.
    if self._ffmpegsumo_name:
      file_path = os.path.join(self._target_dir, self._ffmpegsumo_name)
      urllib.urlretrieve(self._ffmpegsumo_url, file_path)

    # Set permissions.
    for path, _, fnames in os.walk(self._target_dir):
      for fname in fnames:
        os.chmod(os.path.join(path, fname), 0755)
    return True

  def Main(self):
    """main() routine for GetBuild.  Fetch everything.

    Returns:
      Value suitable for process exit code (e.g. 0 on success).
    """
    if (not self.ProcessArgs() or
        not self.CleanUp() or
        not self.DownloadAndExtractFiles()):
      return 1

    # See scripts/master/factory/commands.py's SetBuildPropertyShellCommand
    print 'BUILD_PROPERTY build_id=%s' % self._build_id
    return 0


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--platform',
                           help='builder platform. Required.')
  option_parser.add_option('--build-url',
                           help='URL where to find the build.')
  option_parser.add_option('--archive-url',
                           help='URL containing list of builds. '
                                'If ommited, default archive will be used.')
  option_parser.add_option('--extract', action='store_true',
                            help='Extract downloaded files.')
  option_parser.add_option('--build',
                            help='Specify the build number we should download.'
                                 ' E.g. "45644"')
  build_dir = os.getcwd()
  option_parser.add_option('--build-dir', default=build_dir,
                           help='Path to main build directory (the parent of '
                                'the Release or Debug directory)')
  target_dir = os.path.join(build_dir, 'Release')
  option_parser.add_option('--target-dir', default=target_dir,
                           help='Build target to archive (Release)')

  options, args = option_parser.parse_args()
  if args:
    option_parser.error('Args not supported.')
  gb = GetBuild(options)
  return gb.Main()


if '__main__' == __name__:
  sys.exit(main())
