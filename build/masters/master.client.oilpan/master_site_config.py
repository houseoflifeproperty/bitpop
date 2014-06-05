# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Oilpan(Master.Master3):
  project_name = 'Oilpan'
  master_port = 8032
  slave_port = 8132
  master_port_alt = 8232
  viewvc_url = 'http://src.chromium.org/viewvc/blink?view=revision&revision=%s'
  buildbot_url = 'http://build.chromium.org/p/client.oilpan/'
