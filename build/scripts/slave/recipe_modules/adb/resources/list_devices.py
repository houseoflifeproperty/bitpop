# Copyright (c) 2014 ThE Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generates json output of the adb devices that are online.

Argument 1: the repr() of the adb command to run.
Argument 2: the temporary json file to write the output to.
"""

import subprocess
import sys
import json
import re
import logging

logging.basicConfig(level=0)

cmd = eval(sys.argv[1])
outFileName = sys.argv[2]

output = subprocess.check_output(cmd)
devices = []
for line in output.splitlines():
  logging.info(line)
  m = re.match('^([0-9A-Za-z]+)\s+device$', line)
  if m:
    devices.append(m.group(1))

with open(outFileName, 'w') as outFile:
  json.dump(devices, outFile)
