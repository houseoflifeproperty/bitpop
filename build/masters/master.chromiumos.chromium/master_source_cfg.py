# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller
from master import master_config


helper = master_config.Helper({})
helper.Scheduler('chromium_src', branch='master', treeStableTimer=60)

def Update(config, _active_master, c):
  master_poller = gitiles_poller.GitilesPoller(
      'https://chromium.googlesource.com/chromium/src')
  c['change_source'].append(master_poller)
  return helper.Update(c)
