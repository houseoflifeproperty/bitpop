# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientPorts(Master.NaClBase):
  project_name = 'NativeClientPorts'
  master_port = 8035
  slave_port = 8135
  master_port_alt = 8235
  base_app_url = 'https://naclports-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
