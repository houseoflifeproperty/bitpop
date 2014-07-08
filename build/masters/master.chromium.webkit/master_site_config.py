# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumWebkit(Master.Master1):
  project_name = 'Chromium Webkit'
  master_port = 8014
  slave_port = 8114
  master_port_alt = 8214
  base_app_url = 'https://blink-status.appspot.com'
  tree_status_url = base_app_url + '/status'
