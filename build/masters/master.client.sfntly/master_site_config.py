# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Sfntly(Master.Master3):
  project_name = 'Sfntly'
  project_url = 'http://code.google.com/p/sfntly/'
  master_port = 8048
  slave_port = 8148
  master_port_alt = 8248
  buildbot_url = 'http://build.chromium.org/p/client.sfntly/'
