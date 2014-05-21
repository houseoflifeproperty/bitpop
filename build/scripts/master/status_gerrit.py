# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This is modified version of buildbot/status/status_gerrit.py
# It uses commit hash in event.refUpdate.newRev or event.patchSet.revision,
# instead of got_revision, because GClient update steps may get wrong version
# (it might pick up svn version of sub respository in DEPS).
# Original version supports repo and git, but it only supports git.
# It also pass os.environ to ssh so that you can use ssh-agent.

import os

from buildbot.status import status_gerrit

from twisted.internet import reactor


class GerritStatusPush(status_gerrit.GerritStatusPush):
  """Event streamer to a gerrit ssh server."""

  def buildFinished(self, builderName, build, result):
    project = build.getProperty('project')
    message, verified, reviewed = self.reviewCB(builderName, build, result,
                                               self.reviewArg)
    if 'event.refUpdate.newRev' in build.getProperties():
      # when patchset is landed.
      if verified >= 0 and reviewed >= 0:
        return
      revision = build.getProperty('event.refUpdate.newRev')
    elif 'event.patchSet.revision' in build.getProperties():
      # when patchset is created.
      revision = build.getProperty('event.patchSet.revision')
    else:
      return
    self.sendCodeReview(project, revision, message, verified, reviewed)

  def sendCodeReview(self, project, revision, message=None, verified=0,
                     reviewed=0):
    command = ["ssh", self.gerrit_username + "@" + self.gerrit_server,
               "-p %d" % self.gerrit_port,
               "gerrit", "review",
               "--project %s" % str(project)]
    if message:
      command.append("--message '%s'" % message)
    if verified:
      command.append("--verified %d" % int(verified))
    if reviewed:
      command.append("--code-review %d" % int(reviewed))
    command.append(str(revision))
    print command
    reactor.spawnProcess(self.LocalPP(self), "ssh", command,
                         env=os.environ)
