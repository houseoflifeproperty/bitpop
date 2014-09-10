# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os.path

from common import chromium_utils
from master import chromium_svn_poller


def Update(config, active_master, c):
  poller = chromium_svn_poller.ChromiumSvnPoller()

  c['change_source'].append(poller)
