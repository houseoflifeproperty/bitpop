#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Synchronizes a local directory with a directory on an android device.

This script is not very intelligent, and simply uses the file
size to determine if files are out of date.

The script takes two arguments, a device directory to transfer to, and a
local directory to use to compare

Example:
    transfer_files.py /path/to/adb /device/dir /local/dir

"""
import os
import subprocess
import sys

# ls -la on android produces output like this:
# -rw-r--r-- root     root         4024 1969-12-31 16:00 ueventd.rc
EXP_COLS = 6
FILE_NAME_COL = 6
FILE_SIZE_COL = 3

def main(argv):
  adb = argv[1]
  device_root = argv[2]
  local_root = argv[3]

  files = os.listdir(local_root)

  file_sizes = {afile: os.path.getsize(os.path.join(local_root, afile))
                for afile in files}

  proc = subprocess.Popen([adb, 'shell', 'ls', '-la', device_root],
                          stdout=subprocess.PIPE)
  out = proc.communicate()[0]

  device_file_sizes = {}
  for line in out.splitlines():
    cols = line.split(None, EXP_COLS)
    if len(cols) != EXP_COLS + 1:
      continue
    device_file_sizes[cols[FILE_NAME_COL]] = int(cols[FILE_SIZE_COL])

  files_to_transfer = []
  for afile, size in file_sizes.iteritems():
    if afile in device_file_sizes and device_file_sizes[afile] == size:
      print afile + " found on device, and size matches, skipping"
      continue
    files_to_transfer.append(os.path.join(local_root,  afile))

  for afile in files_to_transfer:
    print afile + " not found on device, pushing"
    subprocess.call([adb, 'push', afile, device_root])

  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))
