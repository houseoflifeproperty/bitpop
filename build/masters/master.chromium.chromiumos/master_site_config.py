# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumChromiumOS(Master.Master1):
  project_name = 'Chromium ChromiumOS'
  master_port = 8052
  slave_port = 8152
  master_port_alt = 8252
  alternate_tree_closing_notification_recipients = [
      'chromeos-build-failures@google.com']
  alternate_tree_status_url = 'https://chromiumos-status.appspot.com'
