# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumWebRTC(Master.Master1):
  project_name = 'Chromium WebRTC'
  master_port = 8054
  slave_port = 8154
  master_port_alt = 8254
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'chromium-webrtc-cb-watchlist@google.com'
  base_app_url = 'https://webrtc-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
