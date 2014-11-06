# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Breakpad(Master.Master3):
  project_name = 'Breakpad'
  project_url = ('https://code.google.com/p/google-breakpad/wiki/'
                 'GettingStartedWithBreakpad')
  master_port = 8053
  slave_port = 8153
  master_port_alt = 8253
  buildbot_url = 'http://build.chromium.org/p/client.breakpad/'
