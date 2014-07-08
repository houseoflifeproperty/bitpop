# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class PushCanary(Master.Base):
  project_name = 'Chromium PushCanary'
  master_host = 'localhost'
  master_port = 8081
  slave_port = 8181
  master_port_alt = 8281
