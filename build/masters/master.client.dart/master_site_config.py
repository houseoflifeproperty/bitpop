# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Dart(Master.Master3):
  base_app_url = 'https://dart-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  # This IP refers to a golem server in BigCluster
  http_status_push_url = "http://108.170.219.8:8080/submit-buildbot-info/"
  project_name = 'Dart'
  master_port = 8040
  slave_port = 8140
  # Enable when there's a public waterfall.
  master_port_alt = 8240
  buildbot_url = 'http://build.chromium.org/p/client.dart/'
