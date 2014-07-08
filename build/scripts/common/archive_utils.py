# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of common operations/utilities for build archiving."""

import glob
import os
import platform
import re
import sys

from common import chromium_utils

# Base name of the database of files to archive.
FILES_FILENAME = 'FILES.cfg'


class StagingError(Exception):
  pass


class Config(object):
  """Defines default values for archival utilities to use."""
  # List of symbol files to save, but not to upload to the symbol server
  # (generally because they have no symbols and thus would produce an error).
  # We have to list all the previous names of icudt*.dll. Now that we
  # use icudt.dll, we don't need to update this file any more next time
  # we pull in a new version of ICU.
  symbols_to_skip_upload = [
      'icudt38.dll', 'icudt42.dll', 'icudt46.dll', 'icudt.dll', 'rlz.dll',
      'avcodec-53.dll', 'avcodec-54.dll', 'avformat-53.dll', 'avformat-54.dll',
      'avutil-51.dll', 'd3dx9_42.dll', 'd3dx9_43.dll', 'D3DCompiler_42.dll',
      'D3DCompiler_43.dll', 'd3dcompiler_46.dll', 'msvcp120.dll',
      'msvcr120.dll', 'xinput1_3.dll', 'widevinecdm.dll', 'FlashPlayerApp.exe',]

  if os.environ.get('CHROMIUM_BUILD', '') == '_google_chrome':
    exes_to_skip_entirely = []
  else:
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
                      'icudtl.dat',
                      'plugins\\npapi_layout_test_plugin.dll',
                     ]

  # Archive everything in these directories, using glob.
  test_dirs_to_archive = ['fonts']
  # Create these directories, initially empty, in the archive.
  test_dirs_to_create = ['plugins', 'fonts']

  archive_host = 'master1.golo.chromium.org'

  if (sys.platform in ['linux', 'linux2', 'darwin'] or
      os.environ.get('BUILDBOT_ARCHIVE_FORCE_SSH')):
    # Directory on archive_host (accessed via ssh)
    www_dir_base = "/home/chrome-bot/www/"
  elif sys.platform in ['cygwin', 'win32']:
    # archive_host SMB share.
    www_dir_base = "\\\\" + archive_host + "\\chrome-bot\\www\\"

  symbol_url = 'http://clients2.google.com/cr/symbol'
  symbol_staging_url = 'http://clients2.google.com/cr/staging_symbol'


class FilesCfgParser(object):
  """Class to process a FILES.cfg style listing of build files."""

  def __init__(self, files_file, buildtype, arch):
    self._buildtype = buildtype
    self._arch = arch
    self._files_cfg = self._ParseFilesCfg(files_file)
    self.files_dict = self._FilterFilesCfg()

  def _SetArch(self, value):
    """Set build arch and reset files_dict to reflect new build criteria."""
    self._arch = value
    self.files_dict.clear()
    self.files_dict.update(self._FilterFilesCfg())

  arch = property(fset=_SetArch)

  def _SetBuildType(self, value):
    """Set build type and reset files_dict to reflect new build criteria."""
    self._buildtype = value
    self.files_dict.clear()
    self.files_dict.update(self._FilterFilesCfg())

  buildtype = property(fset=_SetBuildType)

  def _FilterFilesCfg(self):
    """Return a dict of file items that match the current build criteria."""
    files_dict = {}
    for fileobj in self._files_cfg:
      if self._buildtype not in fileobj['buildtype']:
        continue
      if not fileobj.get('arch') or self._arch in fileobj['arch']:
        files_dict[fileobj['filename']] = fileobj
    return files_dict

  @staticmethod
  def _ParseFilesCfg(files_file):
    """Return the dictionary of archive file info read from the given file."""
    if not os.path.exists(files_file):
      raise StagingError('Files list does not exist (%s).' % files_file)
    exec_globals = {'__builtins__': None}

    execfile(files_file, exec_globals)
    return exec_globals['FILES']

  @classmethod
  def IsDirectArchive(cls, archive_list):
    """Determine if the given archive list should be archived as-is.

      An archive list (from ParseArchiveLists) is archived as-is (not added to
      another archive file) iff:
      - There list contains a single file, and
      - That file has the 'direct_archive' flag or its 'archive' name matches
        its 'filename' (an implied 'direct_archive').
    """
    fileobj = archive_list[0]
    return (len(archive_list) == 1 and
            (fileobj['filename'] == fileobj['archive'] or
             fileobj.get('direct_archive')))

  def IsOptional(self, filename):
    """Determine if the given filename is marked optional for this config."""
    return (self.files_dict.get(filename) and self._buildtype in
            self.files_dict[filename].get('optional', []))

  def ParseGroup(self, filegroup):
    """Return the list of filenames in the given group (e.g. "symbols")."""
    return [fileobj['filename'] for fileobj in self.files_dict.itervalues()
        if (fileobj.get('filegroup') and filegroup in fileobj.get('filegroup'))
    ]

  def ParseArchiveLists(self):
    """Generate a dict of all the file items in all archives."""
    archive_lists = {}
    for fileobj in self.files_dict.itervalues():
      if fileobj.get('archive'):
        archive_lists.setdefault(fileobj['archive'], []).append(fileobj)
    return archive_lists

  def ParseLegacyList(self):
    """Return the list of 'default' filenames.

    Default files are either tagged as "default" filegroup or they have no
    filegroup (i.e. legacy entries from before the filegroup field was added.)
    """
    files_list = [
        fileobj['filename'] for fileobj in self.files_dict.itervalues()
        if (not fileobj.get('archive') and
            (not fileobj.get('filegroup') or 'default' in
             fileobj.get('filegroup')))
    ]
    return files_list


def ParseFilesList(files_file, buildtype, arch):
  """DEPRECATED: Determine the list of archive files for a given release.

  NOTE: This can be removed after 20.x goes stable (or after scripts/common/
  gets versioned on the official builders like site_config is).
  """
  fparser = FilesCfgParser(files_file, buildtype, arch)
  return fparser.ParseLegacyList()


def ExpandWildcards(base_dir, path_list):
  """Accepts a list of paths relative to base_dir and replaces wildcards.

  Uses glob to change all file paths containing wild cards into lists
  of files present on the file system at time of calling.
  """
  if not path_list:
    return []

  regex = re.compile('[*?[]')
  returned_paths = []
  for path_fragment in path_list:
    if regex.search(path_fragment):
      globbed_paths = glob.glob(os.path.join(base_dir, path_fragment))
      new_paths = [
          globbed_path[len(base_dir)+1:]
          for globbed_path in globbed_paths
          if not os.path.isdir(globbed_path)
      ]
      returned_paths.extend(new_paths)
    else:
      returned_paths.append(path_fragment)

  return returned_paths


def ExtractDirsFromPaths(path_list):
  """Extracts a list of unique directory names from a list of paths.

  Given a list of relative paths, e.g. ['foo.txt', 'baz\\bar', 'baz\\bee.txt']
  returns a list of the directories therein (e.g. ['baz']). Does not
  include duplicates in the list.
  """
  return list(filter(None, set(os.path.dirname(path) for path in path_list)))


def BuildArch(target_arch=None):
  """Determine the architecture of the build being processed."""
  if target_arch == 'x64':
    # Just use the architecture specified by the build if it's 64 bit.
    return '64bit'
  elif target_arch:
    raise StagingError('Unknown target_arch "%s"', target_arch)

  if chromium_utils.IsWindows() or chromium_utils.IsMac():
    # Architecture is not relevant for Mac (combines multiple archs in one
    # release) and Win (32-bit only), so just call it 32bit.
    # TODO(mmoss): This might change for Win if we add 64-bit builds.
    return '32bit'
  elif chromium_utils.IsLinux():
    # This assumes we either build natively or build (and run staging) in a
    # chroot, where the architecture of the python executable is the same as
    # the build target.
    # TODO(mmoss): This appears to be true for the current builders. If that
    # changes, we might have to modify the bots to pass in the build
    # architecture when running this script.
    arch = platform.architecture(bits='unknown')[0]
    if arch == 'unknown':
      raise StagingError('Could not determine build architecture')
    return arch
  else:
    raise NotImplementedError('Platform "%s" is not currently supported.' %
                              sys.platform)


def RemoveIgnored(file_list, ignore_list):
  """Return paths in file_list that don't start with a string in ignore_list.

  file_list may contain bare filenames or paths. For paths, only the base
  filename will be compared to to ignore_list.
  """

  def _IgnoreFile(filename):
    """Returns True if filename starts with any string in ignore_list."""
    for ignore in ignore_list:
      if filename.startswith(ignore):
        return True
    return False
  return [x for x in file_list if not _IgnoreFile(os.path.basename(x))]


def VerifyFiles(files_list, build_dir, ignore_list):
  """Ensures that the needed directories and files are accessible.

  Returns a list of file_list items that are not available.
  """
  needed = []
  not_found = []
  needed = RemoveIgnored(files_list, ignore_list)
  for fn in needed:
    # Assume incomplete paths are relative to the build dir.
    if os.path.isabs(fn):
      needed_file = fn
    else:
      needed_file = os.path.join(build_dir, fn)
    if not os.path.exists(needed_file):
      not_found.append(fn)
  return not_found


def CreateArchive(build_dir, staging_dir, files_list, archive_name,
                  allow_missing=True):
  """Put files into an archive dir as well as a zip of said archive dir.

  This method takes the list of files to archive, then prunes non-existing
  files from that list.

  archive_name is the desired name for the output zip file. It is also used as
  the basis for the directory that the files are zipped into. For instance,
  'foo.zip' creates the file foo.zip with the hierarchy foo/*. 'some_archive'
  creates the file 'some_archive' with the hierarhy some_archive_unzipped/*
  (the directory name is different to prevent name conflicts when extracting to
  the directory containing 'some_archive').

  If files_list is empty or has no existing CreateArchive returns ('', '').
  Otherwise, this method returns the archive directory the files are
  copied to and the full path of the zip file in a tuple.
  """

  print 'Creating archive %s ...' % archive_name

  if allow_missing:
    # Filter out files that don't exist.
    filtered_file_list = [f.strip() for f in files_list if
                          os.path.exists(os.path.join(build_dir, f.strip()))]
  else:
    filtered_file_list = list(files_list)

  if not filtered_file_list:
    # We have no files to archive, don't create an empty zip file.
    print 'WARNING: No files to archive.'
    return ('', '')

  if archive_name.endswith('.zip'):
    archive_dirname = archive_name[:-4]
  else:
    archive_dirname = archive_name + '_unzipped'

  (zip_dir, zip_file) = chromium_utils.MakeZip(staging_dir,
                                               archive_dirname,
                                               filtered_file_list,
                                               build_dir,
                                               raise_error=not allow_missing)
  if not os.path.exists(zip_file):
    raise StagingError('Failed to make zip package %s' % zip_file)

  if os.path.basename(zip_file) != archive_name:
    orig_zip = zip_file
    zip_file = os.path.join(os.path.dirname(orig_zip), archive_name)
    print 'Renaming archive: "%s" -> "%s"' % (orig_zip, zip_file)
    chromium_utils.MoveFile(orig_zip, zip_file)
  return (zip_dir, zip_file)
