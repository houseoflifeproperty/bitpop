#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script that can be used to filter out files from a patch/diff.

Usage: pipe the patch contents to stdin and the filtered output will be written
to stdout.
The output will be compatible with the patch program, both for Subversion and
Git patches as input.
"""

import optparse
import os
import re
import sys

from depot_tools_patch import patch

# Subversion patch entries always start with either of the following, according
# to depot_tools/third_party/upload.py.
_SVN_PREFIXES = ('Index: ', 'Property changes on: ')
_GIT_PREFIX = 'diff --git '

_SVN_FILENAME_REGEX = re.compile(r'^.*: ([^\t]+).*\n$')

# The Git patches generated from depot_tools/git_cl.py has the a/ and b/
# prefixes for the source filenames stripped out. To support both normal patches
# and such patches, theyse prefixes are put in optional non-capturing groups.
_GIT_FILENAME_REGEX = re.compile(r'^diff --git (?:a/)?.* (?:b/)?(.*)\n$')


def parse_git_patch_set(patch_contents):
  return _parse_patch_set(_GIT_PREFIX, _GIT_FILENAME_REGEX, patch_contents)


def parse_svn_patch_set(patch_contents):
  return _parse_patch_set(_SVN_PREFIXES, _SVN_FILENAME_REGEX, patch_contents)


def _parse_patch_set(prefix, filename_regex, patch_contents):
  # To support both normal Git patches and ones that has been uploaded with
  # depot_tools/third_party/upload.py (which adds an Subversion-style Index:
  # line before each file entry) we strip out the Index: lines if they exist for
  # Git patches, so we can parse each entry properly. Then they're readded in
  # the convert_to_patch_compatible_diff funtion.
  if prefix == _GIT_PREFIX:
    filtered_lines = filter(lambda line: not line.startswith(_SVN_PREFIXES),
                            patch_contents.splitlines(True))
    patch_contents = ''.join(filtered_lines)

  patch_chunks = []
  current_chunk = []
  for line in patch_contents.splitlines(True):
    if line.startswith(prefix) and current_chunk:
      patch_chunks.insert(0, current_chunk)
      current_chunk = []
    current_chunk.append(line)

  if current_chunk:
    patch_chunks.insert(0, current_chunk)

  # Parse filename for each patch chunk and create FilePatchDiff objects
  patches = []
  for chunk in patch_chunks:
    match = filename_regex.match(chunk[0])
    if not match:
      raise Exception('Did not find any filename in line "%s"' % chunk[0])
    filename = match.group(1).replace('\\', '/')
    patches.append(patch.FilePatchDiff(filename=filename, diff=''.join(chunk),
                                       svn_properties=[]))
  return patch.PatchSet(patches)


def convert_to_patch_compatible_diff(filename, patch_entry):
  """Convert patch data to be compatible with the standard patch program.

  This will remove the "a/" and "b/" prefixes added by Git, so the patch becomes
  compatible with the standard patch program.
  It will also add an Index: line at the first line if not already present, to
  make the patch entry compatible a Subversion patch (so it can be used by the
  standard patch program).
  """
  diff = ''
  patch_lines = patch_entry.splitlines(True)
  if not patch_lines[0].startswith(_SVN_PREFIXES):
    diff += _SVN_PREFIXES[0] + filename + '\n'

  for line in patch_lines:
    if line.startswith('---'):
      line = line.replace('a/' + filename, filename)
    elif line.startswith('+++'):
      line = line.replace('b/' + filename, filename)
    diff += line
  return diff


def main():
  usage = '%s -f <path-filter>' % os.path.basename(sys.argv[0])
  parser = optparse.OptionParser(usage=usage)
  parser.add_option('-f', '--path-filter',
                    help=('The path filter (POSIX paths) that all file paths '
                          'are required to have to pass this filter (no '
                          'regexp).'))
  options, args = parser.parse_args()
  if args:
    parser.error('Unused args: %s' % args)
  if not options.path_filter:
    parser.error('A path filter must be be specified.')

  patch_contents = sys.stdin.read()

  # Find out if it's a Git or Subversion patch set.
  is_git = any(l.startswith(_GIT_PREFIX) for l in patch_contents.splitlines())

  if is_git:
    patchset = parse_git_patch_set(patch_contents)
  else:
    patchset = parse_svn_patch_set(patch_contents)

  # Only print the patch entries that passes our path filter.
  for patch_entry in patchset:
    if patch_entry.filename.startswith(options.path_filter):
      print convert_to_patch_compatible_diff(patch_entry.filename,
                                             patch_entry.get(for_git=False)),

if __name__ == '__main__':
  sys.exit(main())
