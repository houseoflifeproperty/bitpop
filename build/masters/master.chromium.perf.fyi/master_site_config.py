# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumPerfFyi(Master.Master1):
  project_name = 'Chromium Perf Fyi'
  master_port = 8061
  slave_port = 8161
  master_port_alt = 8261
  buildbot_url = 'http://build.chromium.org/p/chromium.perf.fyi/'
