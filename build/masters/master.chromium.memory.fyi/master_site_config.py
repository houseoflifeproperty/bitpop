# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumMemoryFYI(Master.Master1):
  project_name = 'Chromium Memory FYI'
  master_port = 8025
  slave_port = 8125
  master_port_alt = 8225
  buildbot_url = 'http://build.chromium.org/p/chromium.memory.fyi/'
