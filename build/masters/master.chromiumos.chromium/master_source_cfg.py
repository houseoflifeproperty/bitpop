# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common import chromium_utils

from master import chromium_svn_poller
from master import master_config

defaults = {}

helper = master_config.Helper(defaults)
helper.Scheduler('chromium_src', branch='src', treeStableTimer=60)

def Update(config, _active_master, c):
  poller = chromium_svn_poller.ChromiumSvnPoller()
  c['change_source'].append(poller)
  return helper.Update(c)
