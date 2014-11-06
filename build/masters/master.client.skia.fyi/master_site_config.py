# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""


from config_bootstrap import Master


class SkiaFYI(Master.Master3):
  project_name = 'SkiaFYI'
  master_port = 8098
  slave_port = 8198
  master_port_alt = 8298
  repo_url = 'https://skia.googlesource.com/skia.git'
  buildbot_url = 'http://build.chromium.org/p/client.skia.fyi/'
  code_review_site = 'https://codereview.chromium.org'
