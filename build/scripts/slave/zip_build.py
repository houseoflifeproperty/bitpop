#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Creates a zip file in the staging dir with the result of a compile.
    It can be sent to other machines for testing.
"""

import csv
import fnmatch
import glob
import optparse
import os
import re
import shutil
import stat
import sys
import tempfile

from common import chromium_utils
from slave import build_directory
from slave import slave_utils

class StagingError(Exception): pass


class SyzyASanWinFilter():
  def __init__(self, build_dir, target):
    self.root = os.path.abspath(os.path.join(build_dir, target))

  def __call__(self, path):
    """Takes a path to a file and returns the path to its asanified counterpart.

    Returns None if path is already an asanified file (to skip it's archival).
    Returns the original path otherwise.
    """
    syzygy_root = os.path.join(self.root, 'syzygy')
    if syzygy_root in path:
      return None
    asan_root = os.path.join(syzygy_root, 'asan')
    asaned_file = path.replace(self.root, asan_root)
    if os.path.isfile(asaned_file):
      return asaned_file
    return path


PATH_FILTERS = {
    'syzyasan_win': SyzyASanWinFilter,
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


def GetRecentBuildsByBuildNumber(zip_list, zip_base, zip_ext, prune_limit):
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
  # Only keep the last prune_limit number (that means we could have
  # 2*prune_limit due to _old files if someone forced a respin of
  # every single one)
  saved_build_list = build_list[-prune_limit:]
  ordered_asc_by_build_number_list = []
  for saved_build in saved_build_list:
    recent_name = zip_base + ('_%d' % saved_build) + zip_ext
    ordered_asc_by_build_number_list.append(recent_name)
    ordered_asc_by_build_number_list.append(
        recent_name.replace(zip_ext, '_old' + zip_ext))
  return ordered_asc_by_build_number_list


def GetRecentBuildsByModificationTime(zip_list, prune_limit):
  """Return the prune_limit most recent builds by modification time."""
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
  return ordered_asc_by_mtime_list[-prune_limit:]


def FileRegexWhitelist(options):
  if chromium_utils.IsWindows() and options.target is 'Release':
    # Special case for chrome. Add back all the chrome*.pdb files to the list.
    # Also add browser_test*.pdb, ui_tests.pdb and ui_tests.pdb.
    # TODO(nsylvain): This should really be defined somewhere else.
    return (r'^(chrome[_.]dll|chrome[_.]exe'
            # r'|browser_test.+|unit_tests'
            r')\.pdb$')

  return '$NO_FILTER^'


def FileRegexBlacklist(options):
  if chromium_utils.IsWindows():
    # Remove all .ilk/.7z and maybe PDB files
    # TODO(phajdan.jr): Remove package_pdb_files when nobody uses it.
    include_pdbs = options.factory_properties.get('package_pdb_files', True)
    if include_pdbs:
      return r'^.+\.(rc|res|lib|exp|ilk|7z|([pP]recompile\.h\.pch.*))$'
    else:
      return r'^.+\.(rc|res|lib|exp|ilk|pdb|7z|([pP]recompile\.h\.pch.*))$'
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


def MojomJSFiles(build_dir):
  """Lists all mojom JavaScript files that need to be included in the archive.

  Args:
    build_dir: The build directory.

  Returns:
    A list of mojom JavaScript file paths which are relative to the build
    directory.
  """
  walk_dirs = [
    'gen/mojo',
    'gen/content/test/data',
  ]
  mojom_js_files = []
  for walk_dir in walk_dirs:
    walk_dir = os.path.join(build_dir, walk_dir)
    for path, _, files in os.walk(walk_dir):
      rel_path = os.path.relpath(path, build_dir)
      for mojom_js_file in fnmatch.filter(files, '*.mojom.js'):
        mojom_js_files.append(os.path.join(rel_path, mojom_js_file))
  return mojom_js_files


def WriteRevisionFile(dirname, build_revision):
  """Writes a file containing revision number to given directory.
  Replaces the target file in place.

  Args:
    dirname: Directory to write the file in.
    build_revision: Revision number or hash.

  Returns: The path of the written file.
  """
  try:
    # Script only works on python 2.6
    # pylint: disable=E1123
    tmp_revision_file = tempfile.NamedTemporaryFile(
        mode='w', dir=dirname,
        delete=False)
    tmp_revision_file.write('%s' % build_revision)
    tmp_revision_file.close()
    chromium_utils.MakeWorldReadable(tmp_revision_file.name)
    dest_path = os.path.join(dirname,
                             chromium_utils.FULL_BUILD_REVISION_FILENAME)
    shutil.move(tmp_revision_file.name, dest_path)
    return dest_path
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
  and copies (or hardlinks) the file to /foo/bar_baz.zip.

  Returns: A tuple containing three elements: the base filename, the extension
     and the full versioned filename."""
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
  print 'Created versioned archive', versioned_file
  return (zip_base, zip_ext, versioned_file)


def UploadToGoogleStorage(versioned_file, revision_file, build_url, gs_acl):
  if slave_utils.GSUtilCopyFile(versioned_file, build_url, gs_acl=gs_acl):
    raise chromium_utils.ExternalError(
        'gsutil returned non-zero status when uploading %s to %s!' %
        (versioned_file, build_url))
  print 'Successfully uploaded %s to %s' % (versioned_file, build_url)

  # The file showing the latest uploaded revision must be named LAST_CHANGE
  # locally since that filename is used in the GS bucket as well.
  last_change_file = os.path.join(os.path.dirname(revision_file), 'LAST_CHANGE')
  shutil.copy(revision_file, last_change_file)
  if slave_utils.GSUtilCopyFile(last_change_file, build_url, gs_acl=gs_acl):
    raise chromium_utils.ExternalError(
        'gsutil returned non-zero status when uploading %s to %s!' %
        (last_change_file, build_url))
  print 'Successfully uploaded %s to %s' % (last_change_file, build_url)
  os.remove(last_change_file)
  return '/'.join([build_url, os.path.basename(versioned_file)])


def PruneOldArchives(staging_dir, zip_base, zip_ext, prune_limit):
  """Removes old archives so that we don't exceed disk space."""
  zip_list = glob.glob(os.path.join(staging_dir, zip_base + '_*' + zip_ext))
  saved_zip_list = GetRecentBuildsByBuildNumber(
      zip_list, zip_base, zip_ext, prune_limit)
  saved_mtime_list = GetRecentBuildsByModificationTime(zip_list, prune_limit)

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
    self.exclusions = (CommaStrParser(options.exclude_files)
                       + chromium_utils.FileExclusions())

    self.regex_whitelist = FileRegexWhitelist(options)
    self.regex_blacklist = FileRegexBlacklist(options)
    self.exclude_unmatched = options.exclude_unmatched

  def __str__(self):
    return '\n  '.join([
        'Zip rules',
        'Inclusions: %s' % self.inclusions,
        'Exclusions: %s' % self.exclusions,
        "Whitelist regex: '%s'" % self.regex_whitelist,
        "Blacklist regex: '%s'" % self.regex_blacklist,
        'Zip unmatched files: %s' % (not self.exclude_unmatched)])

  def Match(self, filename):
    if filename in self.inclusions:
      return True
    if filename in self.exclusions:
      return False
    if re.match(self.regex_whitelist, filename):
      return True
    if re.match(self.regex_blacklist, filename):
      return False
    return not self.exclude_unmatched


def Archive(options):
  build_dir = build_directory.GetBuildOutputDirectory(options.src_dir)
  build_dir = os.path.abspath(os.path.join(build_dir, options.target))

  staging_dir = slave_utils.GetStagingDir(options.src_dir)
  chromium_utils.MakeParentDirectoriesWorldReadable(staging_dir)

  if not options.build_revision:
    (build_revision, webkit_revision) = slave_utils.GetBuildRevisions(
        options.src_dir, options.webkit_dir, options.revision_dir)
  else:
    build_revision = options.build_revision
    webkit_revision = options.webkit_revision

  append_deps_patch_sha = options.factory_properties.get(
      'append_deps_patch_sha')

  unversioned_base_name, version_suffix = slave_utils.GetZipFileNames(
      options.build_properties, build_revision, webkit_revision,
      use_try_buildnumber=(not append_deps_patch_sha))

  if append_deps_patch_sha:
    deps_sha = os.path.join('src', 'DEPS.sha')
    if os.path.exists(deps_sha):
      sha = open(deps_sha).read()
      version_suffix = '%s_%s' % (version_suffix, sha.strip())
      print 'Appending sha of the patch: %s' % sha
    else:
      print 'DEPS.sha file not found, not appending sha.'

  print 'Full Staging in %s' % staging_dir
  print 'Build Directory %s' % build_dir

  # Include the revision file in tarballs
  WriteRevisionFile(build_dir, build_revision)

  # Copy the crt files if necessary.
  if options.target == 'Debug' and chromium_utils.IsWindows():
    CopyDebugCRT(build_dir)

  # Build the list of files to archive.
  root_files = os.listdir(build_dir)

  # Remove initial\chrome.ilk. The filtering is only done on toplevel files,
  # and we can't exclude everything in initial since initial\chrome.dll.pdb is
  # needed in the archive. (And we can't delete it on disk because that would
  # slow down the next incremental build).
  if 'initial' in root_files:
    # Expand 'initial' directory by its contents, so that initial\chrome.ilk
    # will be filtered out by the blacklist.
    index = root_files.index('initial')
    root_files[index:index+1] = [os.path.join('initial', f)
        for f in os.listdir(os.path.join(build_dir, 'initial'))]

  path_filter = PathMatcher(options)
  print path_filter
  print ('\nActually excluded: %s' %
         [f for f in root_files if not path_filter.Match(f)])

  zip_file_list = [f for f in root_files if path_filter.Match(f)]

  # TODO(yzshen): Once we have swarming support ready, we could use it to
  # archive run time dependencies of tests and remove this step.
  mojom_js_files = MojomJSFiles(build_dir)
  print 'Include mojom JavaScript files: %s' % mojom_js_files
  zip_file_list.extend(mojom_js_files)

  zip_file = MakeUnversionedArchive(build_dir, staging_dir, zip_file_list,
                                    unversioned_base_name, options.path_filter)

  zip_base, zip_ext, versioned_file = MakeVersionedArchive(
      zip_file, version_suffix, options)

  prune_limit = max(0, int(options.factory_properties.get('prune_limit', 10)))
  PruneOldArchives(staging_dir, zip_base, zip_ext, prune_limit=prune_limit)

  # Update the latest revision file in the staging directory
  # to allow testers to figure out the latest packaged revision
  # without downloading tarballs.
  revision_file = WriteRevisionFile(staging_dir, build_revision)

  build_url = (options.build_url or
               options.factory_properties.get('build_url', ''))
  if build_url.startswith('gs://'):
    gs_acl = options.factory_properties.get('gs_acl')
    zip_url = UploadToGoogleStorage(
        versioned_file, revision_file, build_url, gs_acl)
  else:
    slavename = options.build_properties['slavename']
    staging_path = (
        os.path.splitdrive(versioned_file)[1].replace(os.path.sep, '/'))
    zip_url = 'http://' + slavename + staging_path

  print '@@@SET_BUILD_PROPERTY@build_archive_url@"%s"@@@' % zip_url

  return 0


def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('--target',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('--src-dir', default='src',
                           help='path to the top-level sources directory')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--exclude-files', default='',
                           help='Comma separated list of files that should '
                                'always be excluded from the zip.')
  option_parser.add_option('--include-files', default='',
                           help='Comma separated list of files that should '
                                'always be included in the zip.')
  option_parser.add_option('--webkit-dir',
                           help='webkit directory path, relative to --src-dir')
  option_parser.add_option('--revision-dir',
                           help='Directory path that shall be used to decide '
                                'the revision number for the archive, '
                                'relative to --src-dir')
  option_parser.add_option('--build_revision',
                           help='The revision the archive should be at. '
                                'Overrides the revision found on disk.')
  option_parser.add_option('--webkit_revision',
                           help='The revision of webkit the build is at. '
                                'Overrides the revision found on disk.')
  option_parser.add_option('--path-filter',
                           help='Filter to use to transform build zip '
                                '(avail: %r).' % list(PATH_FILTERS.keys()))
  option_parser.add_option('--exclude-unmatched', action='store_true',
                           help='Exclude all files not matched by a whitelist')
  option_parser.add_option('--build-url', default='',
                           help=('Optional URL to which to upload build '
                                 '(overrides build_url factory property)'))
  chromium_utils.AddPropertiesOptions(option_parser)

  options, args = option_parser.parse_args(argv)

  if not options.target:
    options.target = options.factory_properties.get('target', 'Release')
  if not options.webkit_dir:
    options.webkit_dir = options.factory_properties.get('webkit_dir')
  if not options.revision_dir:
    options.revision_dir = options.factory_properties.get('revision_dir')
  options.src_dir = (options.factory_properties.get('zip_build_src_dir')
                     or options.src_dir)

  # When option_parser is passed argv as a list, it can return the caller as
  # first unknown arg.  So throw a warning if we have two or more unknown
  # arguments.
  if args[1:]:
    print 'Warning -- unknown arguments' % args[1:]

  if (options.path_filter is None
      and options.factory_properties.get('syzyasan')
      and chromium_utils.IsWindows()):
    options.path_filter = 'syzyasan_win'

  if options.path_filter:
    options.path_filter = PATH_FILTERS[options.path_filter](
        build_directory.GetBuildOutputDirectory(), options.target)

  return Archive(options)


if '__main__' == __name__:
  sys.exit(main(sys.argv))
