# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumGit(Master.Master1):
  project_name = 'Chromium Git'
  master_port = 8019
  slave_port = 8119
  master_port_alt = 8219
