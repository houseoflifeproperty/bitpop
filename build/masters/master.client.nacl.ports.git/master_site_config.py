# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientPortsGit(Master.NaClBase):
  project_name = 'NativeClientPortsGit'
  master_port = 8039
  slave_port = 8139
  master_port_alt = 8239
  base_app_url = 'https://naclports-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
