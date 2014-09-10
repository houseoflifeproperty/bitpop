#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Upload actual GM results to the cloud to allow for rebaselining."""

import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile

from common.skia import global_constants


IMAGE_FILE_PATTERN = re.compile(r'^([^_]+)_(.+)_([^_]+)\.png$')


def _GSUploadAllImages(src_dir):
  """Upload all image files from src_dir to Google Storage.

  We know that GM wrote out these image files with a filename pattern we
  can use to generate the checksum-based Google Storage paths.
  """
  all_files = sorted(os.listdir(src_dir))
  files_to_upload = [f for f in all_files if f.endswith('.png')]
  print 'Uploading %d GM-actual files to Google Storage...' % (
      len(files_to_upload))
  if not files_to_upload:
    return

  gm_actuals_subdir = 'gm'
  temp_root = tempfile.mkdtemp()
  try:
    # Copy all of the desired files to a staging dir, with new filenames.
    for filename in files_to_upload:
      match = IMAGE_FILE_PATTERN.match(filename)
      if not match:
        print 'Warning: found no images matching pattern "%s"' % filename
        continue
      (hashtype, test, hashvalue) = match.groups()
      src_filepath = os.path.join(src_dir, filename)
      temp_dir = os.path.join(temp_root, gm_actuals_subdir, hashtype, test)
      if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)
      shutil.copy(src_filepath, os.path.join(temp_dir, hashvalue + '.png'))

    # Upload the entire staging dir to Google Storage.
    # At present, this will merge the entire contents of [temp_root]/gm
    # into the existing contents of gs://chromium-skia-gm/gm .
    cmd = ['gsutil', 'cp', '-R', os.path.join(temp_root, gm_actuals_subdir),
           global_constants.GS_GM_BUCKET]
    print ' '.join(cmd)
    subprocess.check_call(cmd)
  finally:
    shutil.rmtree(temp_root)

def _GSUploadJsonFiles(src_dir, builder_name):
  """Upload just the JSON files within src_dir to GS_SUMMARIES_BUCKET.

  Args:
    src_dir: (string) directory to upload contents of
    builder_name: (string) name of the builder whose results are to be
        uploaded.
  """
  all_files = sorted(os.listdir(src_dir))
  files_to_upload = [f for f in all_files if f.endswith('.json')]
  print 'Uploading %d JSON files to Google Storage: %s...' % (
      len(files_to_upload), files_to_upload)
  gs_dest_dir = posixpath.join(global_constants.GS_SUMMARIES_BUCKET,
                               builder_name)
  for filename in files_to_upload:
    src_path = os.path.join(src_dir, filename)
    gs_dest_path = posixpath.join(gs_dest_dir, filename)
    subprocess.check_call(['gsutil', 'cp', src_path, gs_dest_path])

def main(gm_actual_dir, builder_name):
  _GSUploadAllImages(gm_actual_dir)
  _GSUploadJsonFiles(gm_actual_dir, builder_name)


if '__main__' == __name__:
  main(*sys.argv[1:])
