# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Gatekeeper(Master.Master1):
  project_name = 'Chromium Gatekeeper'
  master_port = 8008
  slave_port = 8108
  master_port_alt = 8208
  buildbot_url = 'http://build.chromium.org/p/chromium.gatekeeper/'
