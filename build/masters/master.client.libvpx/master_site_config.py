# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Libvpx(Master.Master3):
  project_name = 'Libvpx'
  master_port = 8037
  slave_port = 8137
  master_port_alt = 8237
  buildbot_url = 'http://build.chromium.org/p/client.libvpx/'
  source_url = 'https://chromium.googlesource.com/webm/libvpx'
