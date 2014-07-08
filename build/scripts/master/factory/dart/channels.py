# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class Channel(object):
  def __init__(self, name, branch, position, category_postfix, priority):
    self.branch = branch
    self.builder_postfix = '-' + name
    self.category_postfix = category_postfix
    self.name = name
    self.position = position
    self.priority = priority
    self.all_deps_path = '/' + branch + '/deps/all.deps'
    self.standalone_deps_path = '/' + branch + '/deps/standalone.deps'
    self.dartium_deps_path = '/' + branch + '/deps/dartium.deps'

# The channel names are replicated in the slave.cfg files for all
# dart waterfalls. If you change anything here please also change it there.
CHANNELS = [
  Channel('be', 'branches/bleeding_edge', 0, '', 4),
  Channel('dev', 'trunk', 1, '-dev', 2),
  Channel('stable', 'branches/1.3', 2, '-stable', 1),
  Channel('integration', 'branches/dartium_integration', 3, '-integration', 3),
]

CHANNELS_BY_NAME = {}
for c in CHANNELS:
  CHANNELS_BY_NAME[c.name] = c
