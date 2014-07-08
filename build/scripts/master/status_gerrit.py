# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This code is based on buildbot/status/status_gerrit.py, but has diverged
# enough that it no longer makes sense to extend GerritStatusPush from that
# module.
#
# This class looks for an 'event.change.number' build property -- which is
# created by the GerritPoller class -- as indication that the build was
# triggered by an uploaded patchset, rather than a branch label update.

import urllib

from buildbot.status.base import StatusReceiverMultiService
from buildbot.status.builder import Results

from common.gerrit_agent import GerritAgent

class GerritStatusPush(StatusReceiverMultiService):
  """Add a comment to a gerrit code review indicating the result of a build."""

  def __init__(self, gerrit_url, buildbot_url):
    StatusReceiverMultiService.__init__(self)
    self.agent = GerritAgent(gerrit_url)
    self.buildbot_url = buildbot_url

  def startService(self):
    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus() # pylint: disable=W0201
    self.status.subscribe(self)

  def builderAdded(self, name, builder):
    return self # subscribe to this builder

  def getMessage(self, builderName, build, result):
    message = "Buildbot finished compiling your patchset\n"
    message += "on configuration: %s\n" % builderName
    message += "The result is: %s\n" % Results[result].upper()
    message += '%sbuilders/%s/builds/%s\n' % (
        self.buildbot_url,
        urllib.quote(build.getProperty('buildername')),
        build.getProperty('buildnumber'))
    return message

  def buildFinished(self, builderName, build, result):
    if 'event.change.number' not in build.getProperties():
      return
    change_number = build.getProperty('event.change.number')
    revision = build.getProperty('revision')
    message = self.getMessage(builderName, build, result)
    verified = '+1' if (result == 0) else '-1'
    path = '/changes/%s/revisions/%s/review' % (change_number, revision)
    body = {'message': message, 'labels': {'Verified': verified}}
    self.agent.request('POST', path, None, body)
