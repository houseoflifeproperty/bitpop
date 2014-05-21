#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Uploads the archived O3D build to chrome-web.

Simply calls the archive_file script with the correct source and target.
"""

import os
import sys

from common import chromium_utils
from slave.chromium import archive_file
from slave import slave_utils


def main(argv):
  o3d_dir = os.path.join(os.getcwd(), 'o3d')
  staging_dir = slave_utils.GetStagingDir(o3d_dir)

  # Find builder name and revision #s.
  builder_name = slave_utils.SlaveBuildName(o3d_dir)
  o3d_rev = str(slave_utils.SubversionRevision(o3d_dir))
  platform = chromium_utils.PlatformName()

  # Upload zip.
  local_zip = os.path.join(staging_dir,
                           'full-build-' + platform + '_' + o3d_rev + '.zip')
  remote_zip = 'snapshots/o3d/' + o3d_rev + '/' + builder_name + '.zip'

  archive_file.UploadFile(local_zip, remote_zip)
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
