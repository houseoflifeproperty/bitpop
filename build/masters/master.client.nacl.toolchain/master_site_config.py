# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientToolchain(Master.NaClBase):
  project_name = 'NativeClientToolchain'
  master_port = 8031
  slave_port = 8131
  master_port_alt = 8231
  buildbot_url = 'http://build.chromium.org/p/client.nacl.toolchain/'
