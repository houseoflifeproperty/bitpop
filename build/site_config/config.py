# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Declares a number of site-dependent variables for use by scripts.

A typical use of this module would be

  import chromium_config as config

  v8_url = config.Master.v8_url
"""

import os

from twisted.spread import banana

from config_bootstrap import config_private # pylint: disable=W0403,W0611
from config_bootstrap import Master # pylint: disable=W0403,W0611

# By default, the banana's string size limit is 640kb, which is unsufficient
# when passing diff's around. Raise it to 100megs. Do this here since the limit
# is enforced on both the server and the client so both need to raise the
# limit.
banana.SIZE_LIMIT = 100 * 1024 * 1024


def DatabaseSetup(buildmaster_config, require_dbconfig=False):
  if os.path.isfile('.dbconfig'):
    values = {}
    execfile('.dbconfig', values)
    if 'password' not in values:
      raise Exception('could not get db password')

    buildmaster_config['db_url'] = 'postgresql://%s:%s@%s/%s' % (
        values['username'], values['password'],
        values.get('hostname', 'localhost'), values['dbname'])
  else:
    assert(not require_dbconfig)


class Archive(config_private.Archive):
  """Build and data archival options."""

  # List of symbol files to save, but not to upload to the symbol server
  # (generally because they have no symbols and thus would produce an error).
  # We have to list all the previous names of icudt*.dll. Now that we
  # use icudt.dll, we don't need to update this file any more next time
  # we pull in a new version of ICU.
  symbols_to_skip_upload = [
      'icudt38.dll', 'icudt42.dll', 'icudt46.dll', 'icudt.dll', 'rlz.dll',
      'avcodec-53.dll', 'avcodec-54.dll', 'avformat-53.dll', 'avformat-54.dll',
      'avutil-51.dll', 'd3dx9_42.dll', 'd3dx9_43.dll', 'D3DCompiler_42.dll',
      'D3DCompiler_43.dll', 'xinput1_3.dll', 'FlashPlayerApp.exe',]

  if os.environ.get('CHROMIUM_BUILD', '') == '_google_chrome':
    exes_to_skip_entirely = []
  else:
    # Skip any filenames (exes, symbols, etc.) starting with these strings
    # entirely, typically because they're not built for this distribution.
    exes_to_skip_entirely = ['rlz']

  # Installer to archive.
  installer_exe = 'mini_installer.exe'

  # Test files to archive.
  tests_to_archive = ['reliability_tests.exe',
                      'test_shell.exe',
                      'automated_ui_tests.exe',
                      'ui_tests.exe',  # For syzygy (binary reorder) test bot
                      'icudt.dll',
                      'icudt38.dll',
                      'icudt42.dll',
                      'icudt46.dll',
                      'plugins\\npapi_layout_test_plugin.dll',
                     ]

  # Archive everything in these directories, using glob.
  test_dirs_to_archive = ['fonts']
  # Create these directories, initially empty, in the archive.
  test_dirs_to_create = ['plugins', 'fonts']

  # Directories in which to store built files, for dev, official, and full
  # builds.
  archive_host = config_private.Archive.archive_host
  www_dir_base = config_private.Archive.www_dir_base


class Distributed(config_private.Distributed):
  # File holding current version information.
  version_file = 'VERSION'
