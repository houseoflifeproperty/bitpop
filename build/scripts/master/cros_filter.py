# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter

def FilterNewSpec(repo, builder, branch='master'):
  """Create a new ChangeFilter that monitors the creation of new spec files.

  Args:
    repo: The repository to watch.
    builder: The name of the cbuildbot config to watch.
    branch: The branch that the specified builder is building on.
  """
  prefix = 'Automatic: Start %s %s ' % (builder, branch)
  return ChangeFilter(lambda change: change.comments.startswith(prefix),
                      repository=repo)
