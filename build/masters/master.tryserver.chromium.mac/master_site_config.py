# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class TryServerChromiumMac(Master.Master4a):
  project_name = 'Chromium Mac Try Server'
  master_port = 8091
  slave_port = 8191
  master_port_alt = 8291
  try_job_port = 8391
  # Select tree status urls and codereview location.
  reply_to = 'chrome-troopers+tryserver@google.com'
  base_app_url = 'https://chromium-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = None
  last_good_blink_url = None
  svn_url = 'svn://svn-mirror.golo.chromium.org/chrome-try/try'
  buildbot_url = 'http://build.chromium.org/p/tryserver.chromium.mac/'
