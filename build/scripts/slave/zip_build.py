#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Creates a zip file in the staging dir with the result of a compile.
    It can be sent to other machines for testing.
"""

import csv
import glob
import optparse
import os
import re
import shutil
import stat
import sys
import tempfile

from common import chromium_utils
from slave import slave_utils

class StagingError(Exception): pass


def ASANFilter(path):
  """Takes a path to a file and returns the path to its asan'd counterpart.

  Returns None if path is already an asan'd file.
  Returns the original path otherwise.
  """
  head, tail = os.path.split(path)
  parts = tail.split('.', 1)
  if len(parts) == 1:
    return path
  if parts[-1].startswith('asan'):  # skip 'foo.asan.exe' entirely
    return None
  parts.insert(1, 'asan')
  asan_path = os.path.join(head, '.'.join(parts))
  if os.path.exists(asan_path):
    return asan_path
  return path


PATH_FILTERS = {
    'asan': ASANFilter,
}


def CopyDebugCRT(build_dir):
  # Copy the relevant CRT DLLs to |build_dir|. We copy DLLs from all versions
  # of VS installed to make sure we have the correct CRT version, unused DLLs
  # should not conflict with the others anyways.
  crt_dlls = glob.glob(
      'C:\\Program Files (x86)\\Microsoft Visual Studio *\\VC\\redist\\'
      'Debug_NonRedist\\x86\\Microsoft.*.DebugCRT\\*.dll')
  for dll in crt_dlls:
    shutil.copy(dll, build_dir)


def GetRecentBuildsByBuildNumber(zip_list, zip_base, zip_ext):
  # Build an ordered list of build numbers we have zip files for.
  regexp = re.compile(zip_base + '_([0-9]+)(_old)?' + zip_ext)
  build_list = []
  for x in zip_list:
    regexp_match = regexp.match(os.path.basename(x))
    if regexp_match:
      build_list.append(int(regexp_match.group(1)))
  # Since we match both ###.zip and ###_old.zip, bounce through a set and back
  # to a list to get an order list of build numbers.
  build_list = list(set(build_list))
  build_list.sort()
  # Only keep the last 10 number (that means we could have 20 due to _old files
  # if someone forced a respin of every single one)
  saved_build_list = build_list[-10:]
  ordered_asc_by_build_number_list = []
  for saved_build in saved_build_list:
    recent_name = zip_base + ('_%d' % saved_build) + zip_ext
    ordered_asc_by_build_number_list.append(recent_name)
    ordered_asc_by_build_number_list.append(
        recent_name.replace(zip_ext, '_old' + zip_ext))
  return ordered_asc_by_build_number_list


def GetRecentBuildsByModificationTime(zip_list):
  """Return the 10 most recent builds by modification time."""
  # Get the modification times for all of the entries in zip_list.
  mtimes_to_files = {}
  for zip_file in zip_list:
    mtime = int(os.stat(zip_file).st_mtime)
    mtimes_to_files.setdefault(mtime, [])
    mtimes_to_files[mtime].append(zip_file)
  # Order all files in our list by modification time.
  mtimes_to_files_keys = mtimes_to_files.keys()
  mtimes_to_files_keys.sort()
  ordered_asc_by_mtime_list = []
  for key in mtimes_to_files_keys:
    ordered_asc_by_mtime_list.extend(mtimes_to_files[key])
  # Return the most recent 10 builds.
  return ordered_asc_by_mtime_list[-10:]


def GetRealBuildDirectory(build_dir, target, factory_properties):
  """Return the build directory."""
  if chromium_utils.IsWindows():
    path_list = [build_dir, target]
  elif chromium_utils.IsLinux():
    path_list = [os.path.dirname(build_dir), 'out', target]
  elif chromium_utils.IsMac():
    is_make_or_ninja = (factory_properties.get('gclient_env', {})
                        .get('GYP_GENERATORS') in ('ninja', 'make'))
    if is_make_or_ninja:
      path_list = [os.path.dirname(build_dir), 'out', target]
    else:
      path_list = [os.path.dirname(build_dir), 'xcodebuild', target]
  else:
    raise NotImplementedError('%s is not supported.' % sys.platform)

  return os.path.abspath(os.path.join(*path_list))


def FileRegexWhitelist(options):
  if chromium_utils.IsWindows() and options.target is 'Release':
    # Special case for chrome. Add back all the chrome*.pdb files to the list.
    # Also add browser_test*.pdb, ui_tests.pdb and ui_tests.pdb.
    # TODO(nsylvain): This should really be defined somewhere else.
    return (r'^(chrome[_.]dll|chrome[_.]exe'
            # r'|browser_test.+|unit_tests'
            # r'|chrome_frame_.*tests'
            r')\.pdb$')

  return '$NO_FILTER^'


def FileRegexBlacklist(options):
  if chromium_utils.IsWindows():
    # Remove all .ilk/.7z and maybe PDB files
    include_pdbs = options.factory_properties.get('package_pdb_files', False)
    if include_pdbs:
      return r'^.+\.(ilk|7z|(precompile\.h\.pch.*))$'
    else:
      return r'^.+\.(ilk|pdb|7z|(precompile\.h\.pch.*))$'
  if chromium_utils.IsMac():
    # The static libs are just built as intermediate targets, and we don't
    # need to pull the dSYMs over to the testers most of the time (except for
    # the memory tools).
    include_dsyms = options.factory_properties.get('package_dsym_files', False)
    if include_dsyms:
      return r'^.+\.(a)$'
    else:
      return r'^.+\.(a|dSYM)$'
  if chromium_utils.IsLinux():
    # object files, archives, and gcc (make build) dependency info.
    return r'^.+\.(o|a|d)$'

  return '$NO_FILTER^'


def FileExclusions():
  all_platforms = ['.landmines', 'obj', 'lib', 'gen']
  # Skip files that the testers don't care about. Mostly directories.
  if chromium_utils.IsWindows():
    # Remove obj or lib dir entries
    return all_platforms + ['cfinstaller_archive', 'installer_archive']
  if chromium_utils.IsMac():
    return all_platforms + [
      # We don't need the arm bits v8 builds.
      'd8_arm', 'v8_shell_arm',
      # pdfsqueeze is a build helper, no need to copy it to testers.
      'pdfsqueeze',
      # We copy the framework into the app bundle, we don't need the second
      # copy outside the app.
      # TODO(mark): Since r28431, the copy in the build directory is actually
      # used by tests.  Putting two copies in the .zip isn't great, so maybe
      # we can find another workaround.
      # 'Chromium Framework.framework',
      # 'Google Chrome Framework.framework',
      # We copy the Helper into the app bundle, we don't need the second
      # copy outside the app.
      'Chromium Helper.app',
      'Google Chrome Helper.app',
      '.deps', 'obj.host', 'obj.target',
    ]
  if chromium_utils.IsLinux():
    return all_platforms + [
      # intermediate build directories (full of .o, .d, etc.).
      'appcache', 'glue', 'googleurl', 'lib.host', 'obj.host',
      'obj.target', 'src', '.deps',
      # scons build cruft
      '.sconsign.dblite',
      # build helper, not needed on testers
      'mksnapshot',
    ]

  return all_platforms


def WriteRevisionFile(dirname, build_revision):
  """Writes a file containing revision number to given directory.
  Replaces the target file in place."""
  try:
    # Script only works on python 2.6
    # pylint: disable=E1123
    tmp_revision_file = tempfile.NamedTemporaryFile(
        mode='w', dir=dirname,
        delete=False)
    tmp_revision_file.write('%d' % build_revision)
    tmp_revision_file.close()
    chromium_utils.MakeWorldReadable(tmp_revision_file.name)
    dest_path = os.path.join(dirname,
                             chromium_utils.FULL_BUILD_REVISION_FILENAME)
    shutil.move(tmp_revision_file.name, dest_path)
  except IOError:
    print 'Writing to revision file in %s failed.' % dirname


def MakeUnversionedArchive(build_dir, staging_dir, zip_file_list,
                           zip_file_name, path_filter):
  """Creates an unversioned full build archive.
  Returns the path of the created archive."""
  (zip_dir, zip_file) = chromium_utils.MakeZip(staging_dir,
                                               zip_file_name,
                                               zip_file_list,
                                               build_dir,
                                               raise_error=True,
                                               path_filter=path_filter)
  chromium_utils.RemoveDirectory(zip_dir)
  if not os.path.exists(zip_file):
    raise StagingError('Failed to make zip package %s' % zip_file)
  chromium_utils.MakeWorldReadable(zip_file)

  # Report the size of the zip file to help catch when it gets too big and
  # can cause bot failures from timeouts during downloads to testers.
  zip_size = os.stat(zip_file)[stat.ST_SIZE]
  print 'Zip file is %ld bytes' % zip_size

  return zip_file


def MakeVersionedArchive(zip_file, file_suffix, options):
  """Takes a file name, e.g. /foo/bar.zip and an extra suffix, e.g. _baz,
  and copies (or hardlinks) the file to /foo/bar_baz.zip."""
  zip_template = os.path.basename(zip_file)
  zip_base, zip_ext = os.path.splitext(zip_template)
  # Create a versioned copy of the file.
  versioned_file = zip_file.replace(zip_ext, file_suffix + zip_ext)
  if os.path.exists(versioned_file):
    # This file already exists. Maybe we are doing a clobber build at the same
    # revision. We can move this file away.
    old_file = versioned_file.replace(zip_ext, '_old' + zip_ext)
    chromium_utils.MoveFile(versioned_file, old_file)
  if chromium_utils.IsWindows():
    shutil.copyfile(zip_file, versioned_file)
  else:
    os.link(zip_file, versioned_file)
  chromium_utils.MakeWorldReadable(versioned_file)
  build_url = options.factory_properties.get('build_url', '')
  if build_url.startswith('gs://'):
    if slave_utils.GSUtilCopyFile(versioned_file, build_url):
      raise chromium_utils.ExternalError('gsutil returned non-zero status!')
  print 'Created versioned archive', versioned_file
  return (zip_base, zip_ext)


def PruneOldArchives(staging_dir, zip_base, zip_ext):
  """Removes old archives so that we don't exceed disk space."""
  zip_list = glob.glob(os.path.join(staging_dir, zip_base + '_*' + zip_ext))
  saved_zip_list = GetRecentBuildsByBuildNumber(zip_list, zip_base, zip_ext)
  saved_mtime_list = GetRecentBuildsByModificationTime(zip_list)

  # Prune zip files not matched by the whitelists above.
  for zip_file in zip_list:
    if zip_file not in saved_zip_list and zip_file not in saved_mtime_list:
      print 'Pruning zip %s.' % zip_file
      chromium_utils.RemoveFile(staging_dir, zip_file)


class PathMatcher(object):
  """Generates a matcher which can be used to filter file paths."""

  def __init__(self, options):
    def CommaStrParser(val):
      return [f.strip() for f in csv.reader([val]).next()]
    self.inclusions = CommaStrParser(options.include_files)
    self.exclusions = CommaStrParser(options.exclude_files) + FileExclusions()

    self.regex_whitelist = FileRegexWhitelist(options)
    self.regex_blacklist = FileRegexBlacklist(options)

  def __str__(self):
    return '\n  '.join(['Zip rules',
                        'Inclusions: %s' % self.inclusions,
                        'Exclusions: %s' % self.exclusions,
                        "Whitelist regex: '%s'" % self.regex_whitelist,
                        "Blacklist regex: '%s'" % self.regex_blacklist])

  def Match(self, filename):
    if filename in self.inclusions:
      return True
    if filename in self.exclusions:
      return False
    if re.match(self.regex_whitelist, filename):
      return True
    if re.match(self.regex_blacklist, filename):
      return False
    return True


def Archive(options):
  src_dir = os.path.abspath(options.src_dir)
  build_dir = GetRealBuildDirectory(options.build_dir, options.target,
                                    options.factory_properties)

  staging_dir = slave_utils.GetStagingDir(src_dir)
  chromium_utils.MakeParentDirectoriesWorldReadable(staging_dir)

  webkit_dir = None
  if options.webkit_dir:
    webkit_dir = os.path.join(src_dir, options.webkit_dir)

  unversioned_base_name, version_suffix = slave_utils.GetZipFileNames(
      options.build_properties, options.build_dir, webkit_dir)

  print 'Full Staging in %s' % staging_dir
  print 'Build Directory %s' % build_dir

  # Include the revision file in tarballs
  build_revision = slave_utils.SubversionRevision(src_dir)
  WriteRevisionFile(build_dir, build_revision)

  # Copy the crt files if necessary.
  if options.target == 'Debug' and chromium_utils.IsWindows():
    CopyDebugCRT(build_dir)

  # Build the list of files to archive.
  root_files = os.listdir(build_dir)
  path_filter = PathMatcher(options)
  print path_filter
  print ('\nActually excluded: %s' %
         [f for f in root_files if not path_filter.Match(f)])

  zip_file_list = [f for f in root_files if path_filter.Match(f)]
  zip_file = MakeUnversionedArchive(build_dir, staging_dir, zip_file_list,
                                    unversioned_base_name, options.path_filter)

  zip_base, zip_ext = MakeVersionedArchive(zip_file, version_suffix, options)
  PruneOldArchives(staging_dir, zip_base, zip_ext)

  # Update the latest revision file in the staging directory
  # to allow testers to figure out the latest packaged revision
  # without downloading tarballs.
  WriteRevisionFile(staging_dir, build_revision)

  return 0


def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('--target',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('--src-dir', default='src',
                           help='path to the top-level sources directory')
  option_parser.add_option('--build-dir', default='chrome',
                           help=('path to main build directory (the parent of '
                                 'the Release or Debug directory)'))
  option_parser.add_option('--exclude-files', default='',
                           help=('Comma separated list of files that should '
                                 'always be excluded from the zip.'))
  option_parser.add_option('--include-files', default='',
                           help=('Comma separated list of files that should '
                                 'always be included in the zip.'))
  option_parser.add_option('--webkit-dir',
                           help='webkit directory path, relative to --src-dir')
  option_parser.add_option('--path-filter',
                           help='Filter to use to transform build zip '
                                '(avail: %r).' % list(PATH_FILTERS.keys()))
  chromium_utils.AddPropertiesOptions(option_parser)

  options, args = option_parser.parse_args(argv)

  if not options.target:
    options.target = options.factory_properties.get('target', 'Release')
  if not options.webkit_dir:
    options.webkit_dir = options.factory_properties.get('webkit_dir')

  # When option_parser is passed argv as a list, it can return the caller as
  # first unknown arg.  So throw a warning if we have two or more unknown
  # arguments.
  if args[1:]:
    print 'Warning -- unknown arguments' % args[1:]

  if options.path_filter is None and options.factory_properties.get('asan'):
    options.path_filter = 'asan'
  options.path_filter = PATH_FILTERS.get(options.path_filter)

  return Archive(options)


if '__main__' == __name__:
  sys.exit(main(sys.argv))
