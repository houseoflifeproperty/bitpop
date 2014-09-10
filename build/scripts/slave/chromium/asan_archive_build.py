#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Creates a zip file of a build and upload it to google storage.

This will be used by the ASAN security tests.

To archive files on Google Storage, set the 'gs_bucket' key in the
--factory-properties to 'gs://<bucket-name>'. To control access to archives,
set the 'gs_acl' key to the desired canned-acl (e.g. 'public-read', see
https://developers.google.com/storage/docs/accesscontrol#extension for other
supported canned-acl values). If no 'gs_acl' key is set, the bucket's default
object ACL will be applied (see
https://developers.google.com/storage/docs/accesscontrol#defaultobjects).

"""

import optparse
import os
import re
import stat
import sys

from common import chromium_utils
from slave import build_directory
from slave import slave_utils

class StagingError(Exception): pass


def ShouldPackageFile(filename, target):
  """Returns true if the file should be a part of the resulting archive."""
  if chromium_utils.IsMac():
    file_filter = '^.+\.(a|dSYM)$'
  elif chromium_utils.IsLinux():
    file_filter = '^.+\.(o|a|d)$'
  else:
    raise NotImplementedError('%s is not supported.' % sys.platform)
  if re.match(file_filter, filename):
    return False

  # Skip files that we don't care about. Mostly directories.
  things_to_skip = chromium_utils.FileExclusions()

  if filename in things_to_skip:
    return False

  return True


def archive(options, args):
  build_dir = build_directory.GetBuildOutputDirectory()
  build_dir = os.path.join(build_dir, options.target)
  src_dir = os.path.abspath(os.path.dirname(options.build_dir))

  staging_dir = slave_utils.GetStagingDir(src_dir)
  build_revision = slave_utils.SubversionRevision(src_dir)
  chromium_utils.MakeParentDirectoriesWorldReadable(staging_dir)

  print 'Staging in %s' % build_dir

  # Build the list of files to archive.
  zip_file_list = [f for f in os.listdir(build_dir)
                   if ShouldPackageFile(f, options.target)]

  subdir = None

  # TODO(nsylvain): We need to move linux to a subdir as well, but aarya is not
  # ready with the server-side change.
  if chromium_utils.IsMac():
    subdir = '%s-%s' % (chromium_utils.PlatformName(),
                        options.target.lower())

  prefix = options.factory_properties.get('asan_archive_name', 'asan')
  zip_file_name = '%s-%s-%s-%d' % (prefix,
                                   chromium_utils.PlatformName(),
                                   options.target.lower(),
                                   build_revision)

  (zip_dir, zip_file) = chromium_utils.MakeZip(staging_dir,
                                               zip_file_name,
                                               zip_file_list,
                                               build_dir,
                                               raise_error=True)
  chromium_utils.RemoveDirectory(zip_dir)
  if not os.path.exists(zip_file):
    raise StagingError('Failed to make zip package %s' % zip_file)
  chromium_utils.MakeWorldReadable(zip_file)

  # Report the size of the zip file to help catch when it gets too big.
  zip_size = os.stat(zip_file)[stat.ST_SIZE]
  print 'Zip file is %ld bytes' % zip_size

  gs_bucket = options.factory_properties.get('gs_bucket', None)
  gs_acl = options.factory_properties.get('gs_acl', None)
  status = slave_utils.GSUtilCopyFile(zip_file, gs_bucket, subdir=subdir,
                                      gs_acl=gs_acl)
  if status:
    raise StagingError('Failed to upload %s to %s. Error %d' % (zip_file,
                                                                gs_bucket,
                                                                status))
  else:
    # Delete the file, it is not needed anymore.
    os.remove(zip_file)

  return status


def main(argv):
  option_parser = optparse.OptionParser()
  option_parser.add_option('--target', default='Release',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('--build-dir', help='ignored')
  chromium_utils.AddPropertiesOptions(option_parser)

  options, args = option_parser.parse_args(argv)
  return archive(options, args)

if '__main__' == __name__:
  sys.exit(main(sys.argv))
