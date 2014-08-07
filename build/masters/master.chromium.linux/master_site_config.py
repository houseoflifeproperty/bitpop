# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumLinux(Master.Master1):
  project_name = 'Chromium Linux'
  master_port = 8087
  slave_port = 8187
  master_port_alt = 8287
  buildbot_url = 'http://build.chromium.org/p/chromium.linux/'
