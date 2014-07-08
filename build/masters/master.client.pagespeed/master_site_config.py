# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class PageSpeed(Master.Master3):
  project_name = 'PageSpeed'
  master_port = 8038
  slave_port = 8138
  master_port_alt = 8238
  tree_closing_notification_recipients = [
      'page-speed-codereview@googlegroups.com']
  # Select tree status urls and codereview location.
  base_app_url = 'https://page-speed-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
