# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.svnpoller import SVNPoller
from buildbot.changes.base import PollingChangeSource
from buildbot.changes.pb import ChangePerspective, PBChangeSource
from twisted.internet import defer

class SvnPollerWithComparator(SVNPoller):
  def __init__(self, comparator, *args, **kwargs):
    self.comparator = comparator
    SVNPoller.__init__(self, *args, **kwargs)

  @defer.inlineCallbacks
  def startService(self):
    # Initialize revision comparator with revisions from all changes
    # known to buildbot.
    yield self.comparator.initialize(self.master.db)
    PollingChangeSource.startService(self)

  def create_changes(self, new_logentries):
    changes = SVNPoller.create_changes(self, new_logentries)
    for change in changes:
      self.comparator.addRevision(change['revision'])
    return changes


class ChangePerspectiveWithComparator(ChangePerspective):
  def __init__(self, comparator, *args, **kwargs):
    self.comparator = comparator
    ChangePerspective.__init__(self, *args, **kwargs)

  def perspective_addChange(self, changedict):
    self.comparator.addRevision(changedict.get('revision'))
    return ChangePerspective.perspective_addChange(self, changedict)


class PBChangeSourceWithComparator(PBChangeSource):
  def __init__(self, comparator, *args, **kwargs):
    self.comparator = comparator
    PBChangeSource.__init__(self, *args, **kwargs)

  def getPerspective(self, _mind, username):
    assert username == self.user
    return ChangePerspectiveWithComparator(
        self.comparator, self.master, self.prefix)
