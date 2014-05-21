# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.chromium_git_poller_bb8 import ChromiumGitPoller

def Update(config, active_master, c):
  poller = ChromiumGitPoller(
      repourl='http://git.chromium.org/chromium/src.git',
      branch='master',
      pollinterval=10,
      revlinktmpl='http://git.chromium.org/gitweb/?p=chromium/src.git;a=commit;h=%s')
  c['change_source'].append(poller)
