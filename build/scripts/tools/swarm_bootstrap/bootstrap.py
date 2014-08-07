# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bootstraps a swarming bot to connect host_url.

See swarming/swarm_bot/bootstrap.py for more details.
"""

# host_url = 'http://foo' is added at the top of this file.
# pylint: disable=E0602

import os
import shutil
import sys
import urllib

if sys.platform in ('cygwin', 'win32'):
  root = '/cygdrive/e/b/swarm_slave'
else:
  root = '/b/swarm_slave'
if os.path.isdir(root):
  print('Warning: deleting %s' % root)
  shutil.rmtree(root, ignore_errors=True)
if not os.path.isdir(root):
  os.makedirs(root)
zip_file = os.path.join(root, 'swarming_bot.zip')
urllib.urlretrieve('%s/get_slave_code' % host_url, zip_file)
os.execv(sys.executable, [sys.executable, zip_file])
