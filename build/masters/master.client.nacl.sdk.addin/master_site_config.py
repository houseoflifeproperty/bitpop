# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientSDKAddIn(Master.NaClBase):
  project_name = 'NativeClientSDKAddIn'
  master_port = 8057
  slave_port = 8157
  master_port_alt = 8257
