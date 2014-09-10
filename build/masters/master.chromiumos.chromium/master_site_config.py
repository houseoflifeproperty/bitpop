# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumOSChromium(Master.Master2):
  project_name = 'ChromiumOS Chromium'
  master_port = 8073
  slave_port = 8173
  master_port_alt = 8273
  buildbot_url = 'http://build.chromium.org/p/chromiumos.chromium/'
