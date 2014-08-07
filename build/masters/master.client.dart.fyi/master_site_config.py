# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class DartFYI(Master.Master3):
  # This IP refers to a golem server in BigCluster
  http_status_push_url = "http://108.170.219.8:8080/submit-buildbot-info/"
  project_name = 'Dart FYI'
  master_port = 8055
  slave_port = 8155
  # Enable when there's a public waterfall.
  master_port_alt = 8255
  buildbot_url = 'http://build.chromium.org/p/client.dart.fyi/'
