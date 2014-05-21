#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A script to build the test archive for O3D selenium testing.

  This script is used by all builders.
"""

import os
import re
import shutil
import subprocess
import sys

from common import chromium_utils as utils
from slave import slave_utils

import config

ARCHIVE_CONFIG_NAME = 'o3d_test_archive.txt'


def UploadFile(src, dst):
  www_base = config.Archive.www_dir_base
  full_dst = os.path.join(www_base, dst)
  dst_dir = os.path.dirname(full_dst)
  if utils.IsWindows():
    print 'copying (%s) to (%s)' % (src, full_dst)
    utils.MaybeMakeDirectory(dst_dir)
    shutil.copyfile(src, full_dst)
    print 'done.'
  else:
    host = config.Archive.archive_host
    print 'copying (%s) to (%s) on (%s)' % (src, full_dst, host)
    utils.SshMakeDirectory(host, dst_dir)
    utils.SshCopyFiles(src, host, full_dst)
    print 'done.'


def GetFilesFromDirectory(directory, excludes=None, only_these_types=None):
  """Gets list of files in directory and all subdirectories.

  Note: This function specifically ignores files with .svn in their path.

  Args:
    directory: abs path to source code for O3D.
    excludes: list of paths to exclude.
    only_these_types: if not None, only files with these extensions will be
      included.
  Returns:
    list of files in the given directory and its subdirectories
  """
  filelist = []
  excludes = excludes or []
  excludes = excludes[:]

  # Convert paths to system standard.
  directory = os.path.normpath(directory)
  for i in range(len(excludes)):
    excludes[i] = os.path.normpath(excludes[i])

  # Walk directory, add all non-excluded files.
  for root, _, files in os.walk(directory):
    # Ignore files with .svn in the path.
    if '.svn' in root:
      continue

    # Ignore files where its path starts with an excluded path.
    do_exclude = False
    for exc in excludes:
      if root.startswith(os.path.join(directory, exc)):
        do_exclude = True
        break
    if do_exclude:
      continue

    for name in files:
      if only_these_types is not None:
        split_name = name.rsplit('.', 1)
        if len(split_name) != 2:
          continue
        if split_name[1] not in only_these_types:
          continue
      filelist.append(os.path.join(root, name))

  return filelist


def GetO3DArchiveFiles(source_root, config_file):
  """Gets list of files to be added to O3D test archive.

  Note: This function will change the current directory.
  Exits program with return code 1 on failure.
  Offers very little xml validation.

  Args:
    source_root: path to source code for O3D.
    config_file: abs path to config that specifies contents of test archive
  Returns:
    list of files to be included in O3D test archive.
  """
  file_list = []
  os.chdir(source_root)

  local_content = {}
  try:
    execfile(config_file, local_content)
  except SyntaxError, e:
    try:
      # Try to construct a human readable error message
      error_message = [
          'There is a syntax error in your configuration file.',
          'Line #%s, character %s:' % (e.lineno, e.offset),
          '"%s"' % re.sub(r'[\r\n]*$', '', e.text)]
    except:
      # Something went wrong, re-raise the original exception
      raise e
    else:
      # Raise a new exception with the human readable message:
      raise Exception('\n'.join(error_message))

  if 'o3d_test_archive_configuration' in local_content:
    archive = local_content['o3d_test_archive_configuration']
  else:
    print 'No o3d_test_archive_configuration defined in %s' % config_file
    archive = []

  for profile in archive:
    platform_type = profile['name']

    # Do not add files for platforms that we are not running on.
    if platform_type == 'win' and not utils.IsWindows():
      continue
    if platform_type == 'mac' and not utils.IsMac():
      continue
    if platform_type == 'linux' and not utils.IsLinux():
      continue

    print 'Adding files from profile:', platform_type

    # Add files for profile.
    for item in profile['list']:
      path = item['path']
      if os.path.isfile(path):
        file_list += [path]

      elif os.path.isdir(path):
        if 'excludes' in item:
          excludes = item['excludes']
        else:
          excludes = []
        if 'types' in item:
          types = item['types']
        else:
          types = None
        file_list += GetFilesFromDirectory(path, excludes, types)
  return file_list


def BuildChangeResolution(sourcedir):
  """Build ChangeResolution tool used by tests.

  Note: This function will change the current directory.
  Exits program with return code 1 on failure.

  Args:
    sourcedir: path to source code for O3D.
  """
  build_dir = os.path.join(sourcedir, 'o3d', 'tests', 'lab', 'ChangeResolution')
  print 'Build dir:"%s"' % build_dir
  os.chdir(build_dir)

  if utils.IsWindows():
    env = dict(os.environ)
    our_process = subprocess.Popen(['build.bat'],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   env=env,
                                   universal_newlines=True)

    # Read output so that process isn't blocked with a filled buffer.
    output = our_process.stdout.readlines()
    for line in output:
      print line

    our_process.wait()
    return_code = our_process.returncode

    if return_code != 0:
      print 'ChangeResolution failed to build.'
      print 'Exiting...'
      sys.exit(1)


def main(argv):
  if len(argv) != 3:
    print 'Usage: prepare_selenium_tests.py <o3d_src_root> <destination>'
    print 'Exiting...'
    return 1

  # Make given directories absolute before changing the working directory.
  src_root = os.path.abspath(argv[1])
  o3d_dir = os.path.join(src_root, 'o3d')
  o3d_internal_dir = os.path.join(src_root, 'o3d-internal')
  destination = os.path.abspath(argv[2])
  config_dir = os.path.abspath(os.path.dirname(__file__))
  config_file = os.path.join(config_dir, ARCHIVE_CONFIG_NAME)

  print 'O3D source root:', src_root
  print 'Destination:', destination
  print 'Config file:', config_file

  # Change umask on linux so that outputs (latest file and zip) are readable.
  if utils.IsLinux():
    mask = os.umask(0022)

  # Build ChangeResolution project.
  BuildChangeResolution(src_root)

  # Create test archive.
  files = GetO3DArchiveFiles(src_root, config_file)
  zip_name = 'o3d'
  utils.MakeZip(destination, zip_name, files, src_root)
  zip_path = os.path.join(destination, zip_name + '.zip')
  print 'Zip archive created: %s' % zip_path

  # Find builder name and revision #s.
  builder_name = slave_utils.SlaveBuildName(o3d_dir)
  o3d_rev = str(slave_utils.SubversionRevision(o3d_dir))
  o3d_internal_rev = str(slave_utils.SubversionRevision(o3d_internal_dir))
  package_name = 'test_' + builder_name + '.zip'
  package_dir = o3d_rev + '_' + o3d_internal_rev
  package_path = package_dir + '/' + package_name

  print 'Builder name:', builder_name
  print 'O3D revision:', o3d_rev
  print 'O3D-internal revision:', o3d_internal_rev
  print 'Package path:', package_path

  # Create latest file.
  latest_path = os.path.join(destination, 'latest_' + builder_name)
  file(latest_path, 'w').write(package_path)

  # Upload files.
  package_dst = ('snapshots/o3d/test_packages/o3d/' + package_dir + '/' +
                  package_name)
  latest_dst = 'snapshots/o3d/test_packages/o3d/latest_' + builder_name

  UploadFile(zip_path, package_dst)
  UploadFile(latest_path, latest_dst)

  # Reset the umask on linux.
  if utils.IsLinux():
    os.umask(mask)

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
