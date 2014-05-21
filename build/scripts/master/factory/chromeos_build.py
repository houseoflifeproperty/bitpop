# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Inherits buildbot.process.base.Build to enforce revision = None on source
stamps."""

from master.factory import build


class Build(build.Build):
  """Build class that always uses computeSourceRevision from a source.Source."""

  def getSourceStamp(self):
    source_stamp = build.Build.getSourceStamp(self)
    source_stamp.revision = None
    return source_stamp
