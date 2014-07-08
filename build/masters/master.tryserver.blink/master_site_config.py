# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class BlinkTryServer(Master.Master4):
  project_name = 'Blink Try Server'
  master_port = 8009
  slave_port = 8109
  master_port_alt = 8209
  # Select tree status urls and codereview location.
  reply_to = 'chrome-troopers+tryserver@google.com'
  base_app_url = 'https://chromium-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  last_good_blink_url = 'http://blink-status.appspot.com/lkgr'
