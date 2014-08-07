# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientTryServer(Master.Master4):
  project_name = 'NativeClient-Try'
  master_port = 8029
  slave_port = 8129
  master_port_alt = 8229
  try_job_port = 8329
  reply_to = 'chrome-troopers+tryserver@google.com'
  svn_url = 'svn://svn-mirror.golo.chromium.org/chrome-try/try-nacl'
  buildbot_url = 'http://build.chromium.org/p/tryserver.nacl/'
