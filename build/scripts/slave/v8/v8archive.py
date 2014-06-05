#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Creates a zip file in the staging dir with the result of a compile.
    It can be sent to other machines for testing.
"""

import glob
import optparse
import os
import re
import shutil
import stat
import sys

from common import archive_utils
from common import chromium_utils
from slave import slave_utils

class StagingError(Exception): pass

def MakeWorldReadable(path):
  """Change the permissions of the given path to make it world-readable.
  This is often needed for archived files, so they can be served by web servers
  or accessed by unprivileged network users."""
  perms = stat.S_IMODE(os.stat(path)[stat.ST_MODE])
  os.chmod(path, perms | 0444)


def main(options, args):
  # Create some variables
  src_dir = os.path.abspath(options.src_dir)
  build_dir = os.path.dirname(options.build_dir)
  staging_dir = slave_utils.GetStagingDir(src_dir)
  build_revision = slave_utils.SubversionRevision(src_dir)
  build_version = str(build_revision)

  if chromium_utils.IsMac() or chromium_utils.IsLinux():
    # Files are created umask 077 by default, we need to make sure the staging
    # dir can be fetch from, do this by recursively chmoding back up to the root
    # before pushing to web server.
    a_path = staging_dir
    while a_path != '/':
      current_permissions = os.stat(a_path)[0]
      if current_permissions & 0555 == 0555:
        break
      print 'Fixing permissions (%o) for \'%s\'' % (current_permissions, a_path)
      os.chmod(a_path, current_permissions | 0555)
      a_path = os.path.dirname(a_path)

  print 'Full Staging in %s' % build_dir

  zip_file_list = ['out/%s/d8' % options.target,
                   'out/%s/cctest' % options.target]

  # Write out the revision number so we can figure it out in extract_build.py.
  build_revision_file_name = 'FULL_BUILD_REVISION'
  build_revision_path = os.path.join(build_dir, build_revision_file_name)
  try:
    build_revision_file = open(build_revision_path, 'w')
    build_revision_file.write('%d' % build_revision)
    build_revision_file.close()
    if chromium_utils.IsMac() or chromium_utils.IsLinux():
      os.chmod(build_revision_path, 0644)
    zip_file_list.append(build_revision_file_name)
  except IOError:
    print 'Writing to revision file %s failed ' % build_revision_path

  zip_file_name = 'full-build-%s' % chromium_utils.PlatformName()
  (zip_dir, zip_file) = chromium_utils.MakeZip(staging_dir,
                                               zip_file_name,
                                               zip_file_list,
                                               build_dir,
                                               raise_error=True)
  chromium_utils.RemoveDirectory(zip_dir)
  if not os.path.exists(zip_file):
    raise StagingError('Failed to make zip package %s' % zip_file)
  if chromium_utils.IsMac() or chromium_utils.IsLinux():
    os.chmod(zip_file, 0644)

  # Report the size of the zip file to help catch when it gets too big and
  # can cause bot failures from timeouts during downloads to testers.
  zip_size = os.stat(zip_file)[stat.ST_SIZE]
  print 'Zip file is %ld bytes' % zip_size

  # Create a versioned copy of the file.
  versioned_file = zip_file.replace('.zip', '_%d.zip' % build_revision)
  if os.path.exists(versioned_file):
    # This file already exists. Maybe we are doing a clobber build at the same
    # revision. We can move this file away.
    old_file = versioned_file.replace('.zip', '_old.zip')
    chromium_utils.MoveFile(versioned_file, old_file)
  shutil.copyfile(zip_file, versioned_file)
  if chromium_utils.IsMac() or chromium_utils.IsLinux():
    os.chmod(versioned_file, 0644)

  # Now before we finish, trim out old builds to make sure we don't
  # fill the disk completely.

  zip_template = os.path.basename(zip_file)
  stage_dir = os.path.dirname(zip_file)
  regexp = re.compile(zip_template.replace('.zip', '_([0-9]+)(_old)?.zip'))
  zip_list = glob.glob(os.path.join(stage_dir,
                                    zip_template.replace('.zip', '_*.zip')))
  # Build an ordered list of build numbers we have zip files for.
  build_list = []
  for x in zip_list:
    regexp_match = regexp.match(os.path.basename(x))
    if regexp_match:
      build_list.append(int(regexp_match.group(1)))
  # Since we match both ###.zip and ###_old.zip, bounce through a set and back
  # to a list to get an order list of build numbers.
  build_list = list(set(build_list))
  build_list.sort()
  # Only keep the last 15 number (that means we could have 30 due to _old files
  # if someone forced a respin of every single one)
  trim_build_list = build_list[:-15]
  for x in trim_build_list:
    prune_name = zip_template.replace('.zip', '_%d.zip' % x)
    print 'Pruning build %d' % x
    chromium_utils.RemoveFile(stage_dir, prune_name)
    chromium_utils.RemoveFile(stage_dir, prune_name.replace('.zip', '_old.zip'))

  www_dir = archive_utils.Config.www_dir_base + 'v8_archive/' + build_version
  archive_host = 'master3.golo.chromium.org'
  print 'SshMakeDirectory(%s, %s)' % (archive_host,
                                      www_dir)
  print 'SshCopyFiles(%s, %s, %s)' % (versioned_file,
                                      archive_host,
                                      www_dir)

  chromium_utils.SshMakeDirectory(archive_host, www_dir)
  MakeWorldReadable(versioned_file)
  chromium_utils.SshCopyFiles(versioned_file, archive_host,
                              www_dir)
#  os.unlink(versioned_file)
  # Files are created umask 077 by default, so make it world-readable
  # before pushing to web server.
  return 0


if '__main__' == __name__:
  option_parser = optparse.OptionParser()

  option_parser.add_option('', '--target', default='Release',
      help='build target to archive (Debug or Release)')
  option_parser.add_option('', '--src-dir', default='src',
                           help='path to the top-level sources directory')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--include-files', default=None,
                           help='files that should be included in the'
                                'zip, regardless of any exclusion patterns')

  new_options, new_args = option_parser.parse_args()
  sys.exit(main(new_options, new_args))
