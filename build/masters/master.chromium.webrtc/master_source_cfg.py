# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common import chromium_utils

from master import build_utils
from master.chromium_svn_poller import ChromiumSvnPoller


def Update(config, c):
  poller = ChromiumSvnPoller(pollinterval=30)

  c['change_source'].append(poller)
