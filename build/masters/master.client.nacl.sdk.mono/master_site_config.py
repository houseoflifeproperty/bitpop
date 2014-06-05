# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientSDKMono(Master.NaClBase):
  project_name = 'NativeClientSDKMono'
  master_port = 8050
  slave_port = 8150
  master_port_alt = 8250
