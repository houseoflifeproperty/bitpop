# Copyright (c) 2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A slave that reboots after each job.

Yeah, we trust our unit tests *that* much.
"""

from buildbot.buildslave import BuildSlave


class AutoRebootBuildSlave(BuildSlave):
  def __init__(self, *args, **kwargs):
    """Enforces max_builds == 1 for obvious reasons."""
    kwargs['max_builds'] = 1
    BuildSlave.__init__(self, *args, **kwargs)

  def buildFinished(self, sb):
    """This is called when a build on this slave is finished."""
    return self.shutdown()
