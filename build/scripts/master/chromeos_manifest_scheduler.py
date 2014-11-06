# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re

from buildbot.changes.filter import ChangeFilter
from buildbot.changes.gitpoller import GitPoller
from buildbot.process.properties import Properties
from buildbot.schedulers.basic import SingleBranchScheduler, AnyBranchScheduler
from twisted.internet import defer, utils
from twisted.python import log


def FilterNewSpec(repo, builder, branch='master'):
  """Create a new ChangeFilter that monitors the creation of new spec files.

  Args:
    repo: The repository to watch.
    builder: The name of the cbuildbot config to watch.
    branch: The branch that the specified builder is building on.
  """
  def checkChange(change):
    for line in change.comments.splitlines():
      if line.startswith('Automatic: Start %s %s ' % (builder, branch)):
        return True
    return False
  return ChangeFilter(checkChange, repository=repo)


class _AddBuildIdMixin(object):
  """MixIn that adds 'the _addBuildIdProperty' function to a class."""

  BUILD_ID_RE = re.compile(r'CrOS-Build-Id: (.+)')

  @staticmethod
  def _cleanMasterBuildId(value):
    try:
      return int(value.strip())
    except ValueError, e:
      log.msg("Identified invalid build ID [%s]: %s" % (value, e))
    return None

  @classmethod
  def _getMasterBuildId(cls, change):
    for line in change.get('comments', '').splitlines():
      match = cls.BUILD_ID_RE.match(line)
      if match:
        return cls._cleanMasterBuildId(match.group(1))
    return None

  @defer.inlineCallbacks
  def _addBuildIdProperty(self, changeids, properties=None):
    """Adds the 'master_build_id' property if specified in the change log."""
    if not properties:
      properties = Properties()

    if len(changeids) == 1:
      change = yield self.master.db.changes.getChange(changeids[0])

      master_build_id = self._getMasterBuildId(change)
      if master_build_id:
        properties.setProperty('master_build_id', master_build_id,
                               'Scheduler')
    defer.returnValue(properties)


class ChromeOSManifestSingleBranchScheduler(SingleBranchScheduler,
                                            _AddBuildIdMixin):
  """Augmented 'SingleBranchScheduler' that recognizes CROS build properties"""

  # Overrides 'SingleBranchScheduler.addBuildsetForChanges'
  @defer.inlineCallbacks
  def addBuildsetForChanges(self, *args, **kwargs):
    kwargs['properties'] = yield self._addBuildIdProperty(
        kwargs.get('changeids', ()),
        kwargs.get('properties'),
    )

    rv = yield SingleBranchScheduler.addBuildsetForChanges(
        self,
        *args,
        **kwargs)
    defer.returnValue(rv)


class ChromeOSManifestAnyBranchScheduler(AnyBranchScheduler, _AddBuildIdMixin):
  """Augmented 'AnyBranchScheduler' that recognizes CROS build properties"""

  # Overrides 'AnyBranchScheduler.addBuildsetForChanges'
  @defer.inlineCallbacks
  def addBuildsetForChanges(self, *args, **kwargs):
    kwargs['properties'] = yield self._addBuildIdProperty(
        kwargs.get('changeids', ()),
        kwargs.get('properties'),
    )

    rv = yield AnyBranchScheduler.addBuildsetForChanges(
        self,
        *args,
        **kwargs)
    defer.returnValue(rv)


class CommentRespectingGitPoller(GitPoller):
  """A subclass of the BuildBot GitPoller that doesn't wreck comment newlines.
  """

  # Overrides 'buildbot.changes.gitpoller._get_commit_comments'
  def _get_commit_comments(self, rev):
    args = ['log', rev, '--no-walk', r'--format=%B%n']
    d = utils.getProcessOutput(self.gitbin, args, path=self.workdir,
        env=os.environ, errortoo=False )
    def process(git_output):
      stripped_output = git_output.strip().decode(self.encoding)
      if len(stripped_output) == 0:
        raise EnvironmentError('could not get commit comment for rev')
      return stripped_output
    d.addCallback(process)
    return d
