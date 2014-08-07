# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClient(Master.NaClBase):
  project_name = 'NativeClient'
  master_port = 8030
  slave_port = 8130
  master_port_alt = 8230
  buildbot_url = 'http://build.chromium.org/p/client.nacl/'
