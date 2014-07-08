# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumMac(Master.Master1):
  project_name = 'Chromium Mac'
  master_port = 8086
  slave_port = 8186
  master_port_alt = 8286
  buildbot_url = 'http://build.chromium.org/p/chromium.mac/'
