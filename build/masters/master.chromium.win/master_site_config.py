# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

import socket

class ChromiumWin(object):
  project_name = 'Chromium Win'
  master_port = 8085
  slave_port = 8185
  master_port_alt = 8285
  tree_closing_notification_recipients = []
  from_address = 'buildbot@chromium.org'
  master_host = 'master1.golo.chromium.org'
  is_production_host = socket.getfqdn() == master_host
  buildslave_version = 'buildbot_slave_8_4'
  twisted_version = 'twisted_10_2'
  base_app_url = 'https://chromium-status.appspot.com'
  tree_status_url = base_app_url + '/status'
