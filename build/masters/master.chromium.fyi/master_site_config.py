# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumFYI(Master.Master1):
  project_name = 'Chromium FYI'
  master_port = 8011
  slave_port = 8111
  master_port_alt = 8211
  buildbot_url = 'http://build.chromium.org/p/chromium.fyi/'
  reboot_on_step_timeout = True
