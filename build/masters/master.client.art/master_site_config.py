# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ART(Master.Master3):
  project_name = 'ART'
  master_port = 8200
  slave_port = 8300
  master_port_alt = 8400
  buildbot_url = 'http://build.chromium.org/p/client.art/'
