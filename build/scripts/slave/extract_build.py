#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to extract a build, executed by a buildbot slave.
"""

import optparse
import os
import shutil
import sys
import traceback
import urllib
import urllib2

from common import chromium_utils
from slave import build_directory
from slave import slave_utils

class ExtractHandler(object):
  def __init__(self, url, archive_name):
    self.url = url
    self.archive_name = archive_name


class GSHandler(ExtractHandler):
  def is_present(self):
    return 0 == slave_utils.GSUtilListBucket(self.url, ['-l'])[0]

  def download(self):
    status = slave_utils.GSUtilCopy(self.url, '.')
    if 0 != status:
      return False
    try:
      shutil.move(os.path.basename(self.url), self.archive_name)
    except OSError:
      os.remove(self.archive_name)
      shutil.move(os.path.basename(self.url), self.archive_name)
    return True


class WebHandler(ExtractHandler):
  def is_present(self):
    try:
      content = urllib2.urlopen(self.url)
      content.close()
    except urllib2.HTTPError:
      return False
    return True

  @chromium_utils.RunAndPrintDots
  def download(self):
    try:
      rc = urllib.urlretrieve(self.url, self.archive_name)
      print '\nDownload complete'
    except IOError:
      print '\nFailed to download build'
      return False
    return rc


def GetBuildUrl(options, build_revision, webkit_revision=None):
  """Compute the url to download the build from.  This will use as a base
     string, in order of preference:
     0) options.build_archive_url
     1) options.build_url
     2) options.factory_properties.build_url
     3) build url constructed from build_properties.  This last type of
        construction is not compatible with the 'force build' button.

     Args:
       options: options object as specified by parser below.
       build_revision: Revision for the build.
       webkit_revision: WebKit revision (optional)
  """
  if options.build_archive_url:
    return options.build_archive_url, None

  base_filename, version_suffix = slave_utils.GetZipFileNames(
      options.build_properties, build_revision, webkit_revision, extract=True)

  replace_dict = dict(options.build_properties)
  # If builddir isn't specified, assume buildbot used the builder name
  # as the root folder for the build.
  if not replace_dict.get('parent_builddir') and replace_dict.get('parentname'):
    replace_dict['parent_builddir'] = replace_dict.get('parentname', '')
  replace_dict['base_filename'] = base_filename
  url = options.build_url or options.factory_properties.get('build_url')
  if not url:
    url = ('http://%(parentslavename)s/b/build/slave/%(parent_builddir)s/'
           'chrome_staging')
  if url[-4:] != '.zip': # assume filename not specified
    # Append the filename to the base URL. First strip any trailing slashes.
    url = url.rstrip('/')
    url = '%s/%s' % (url, '%(base_filename)s.zip')
  url = url % replace_dict
  archive_name = url.split('/')[-1]
  versioned_url = url.replace('.zip', version_suffix + '.zip')
  return versioned_url, archive_name


def real_main(options):
  """ Download a build, extract it to build\BuildDir\full-build-win32
      and rename it to build\BuildDir\Target
  """
  abs_build_dir = os.path.abspath(
      build_directory.GetBuildOutputDirectory(options.src_dir))
  target_build_output_dir = os.path.join(abs_build_dir, options.target)

  # Generic name for the archive.
  archive_name = 'full-build-%s.zip' % chromium_utils.PlatformName()

  # Just take the zip off the name for the output directory name.
  output_dir = os.path.join(abs_build_dir, archive_name.replace('.zip', ''))

  src_dir = os.path.dirname(abs_build_dir)
  if not options.build_revision and not options.build_archive_url:
    (build_revision, webkit_revision) = slave_utils.GetBuildRevisions(
        src_dir, options.webkit_dir, options.revision_dir)
  else:
    build_revision = options.build_revision
    webkit_revision = options.webkit_revision
  url, archive_name = GetBuildUrl(options, build_revision, webkit_revision)
  if archive_name is None:
    archive_name = 'build.zip'
    base_url = None
  else:
    base_url = '/'.join(url.split('/')[:-1] + [archive_name])

  if url.startswith('gs://'):
    handler = GSHandler(url=url, archive_name=archive_name)
  else:
    handler = WebHandler(url=url, archive_name=archive_name)

  # We try to download and extract 3 times.
  for tries in range(1, 4):
    print 'Try %d: Fetching build from %s...' % (tries, url)

    failure = False

    # Check if the url exists.
    if not handler.is_present():
      print '%s is not found' % url
      failure = True

      # When 'halt_on_missing_build' is present in factory_properties and if
      # 'revision' is set in build properties, we assume the build is
      # triggered automatically and so we halt on a missing build zip.  The
      # other case is if the build is forced, in which case we keep trying
      # later by looking for the latest build that's available.
      if (options.factory_properties.get('halt_on_missing_build', False) and
          'revision' in options.build_properties and
          options.build_properties['revision'] != ''):
        return slave_utils.ERROR_EXIT_CODE

    # If the url is valid, we download the file.
    if not failure:
      if not handler.download():
        failure = True

    # If the versioned url failed, we try to get the latest build.
    if failure:
      if url.startswith('gs://') or not base_url:
        continue
      else:
        print 'Fetching latest build at %s' % base_url
        base_handler = handler.__class__(base_url, handler.archive_name)
        if not base_handler.download():
          continue

    print 'Extracting build %s to %s...' % (archive_name, abs_build_dir)
    try:
      chromium_utils.RemoveDirectory(target_build_output_dir)
      chromium_utils.ExtractZip(archive_name, abs_build_dir)
      # For Chrome builds, the build will be stored in chrome-win32.
      if 'full-build-win32' in output_dir:
        chrome_dir = output_dir.replace('full-build-win32', 'chrome-win32')
        if os.path.exists(chrome_dir):
          output_dir = chrome_dir

      print 'Moving build from %s to %s' % (output_dir, target_build_output_dir)
      shutil.move(output_dir, target_build_output_dir)
    except (OSError, IOError, chromium_utils.ExternalError):
      print 'Failed to extract the build.'
      # Print out the traceback in a nice format
      traceback.print_exc()
      # Try again...
      continue

    # If we got the latest build, then figure out its revision number.
    if failure:
      print "Trying to determine the latest build's revision number..."
      try:
        build_revision_file_name = os.path.join(
            target_build_output_dir,
            chromium_utils.FULL_BUILD_REVISION_FILENAME)
        build_revision_file = open(build_revision_file_name, 'r')
        print 'Latest build is revision: %s' % build_revision_file.read()
        build_revision_file.close()
      except IOError:
        print "Could not determine the latest build's revision number"

    if failure:
      # We successfully extracted the archive, but it was the generic one.
      return slave_utils.WARNING_EXIT_CODE
    return 0

  # If we get here, that means that it failed 3 times. We return a failure.
  return slave_utils.ERROR_EXIT_CODE


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option('--target',
                           help='build target to archive (Debug or Release)')
  option_parser.add_option('--src-dir', default='src',
                           help='path to the top-level sources directory')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--build-url',
                           help='Base url where to find the build to extract')
  option_parser.add_option('--build-archive-url',
                           help='Exact url where to find the build to extract')
  # TODO(cmp): Remove --halt-on-missing-build when the buildbots are upgraded
  #            to not use this argument.
  option_parser.add_option('--halt-on-missing-build', action='store_true',
                           help='whether to halt on a missing build')
  option_parser.add_option('--build_revision',
                           help='Revision of the build that is being '
                                'archived. Overrides the revision found on '
                                'the local disk')
  option_parser.add_option('--webkit_revision',
                           help='Webkit revision of the build that is being '
                                'archived. Overrides the revision found on '
                                'the local disk')
  option_parser.add_option('--webkit-dir', help='WebKit directory path, '
                                                'relative to the src/ dir.')
  option_parser.add_option('--revision-dir',
                           help=('Directory path that shall be used to decide '
                                 'the revision number for the archive, '
                                 'relative to the src/ dir.'))
  option_parser.add_option('--build-output-dir', help='ignored')
  chromium_utils.AddPropertiesOptions(option_parser)

  options, args = option_parser.parse_args()
  if args:
    print 'Unknown options: %s' % args
    return 1

  if not options.target:
    options.target = options.factory_properties.get('target', 'Release')
  if not options.webkit_dir:
    options.webkit_dir = options.factory_properties.get('webkit_dir')
  if not options.revision_dir:
    options.revision_dir = options.factory_properties.get('revision_dir')
  options.src_dir = (options.factory_properties.get('extract_build_src_dir')
                     or options.src_dir)

  return real_main(options)


if '__main__' == __name__:
  sys.exit(main())
