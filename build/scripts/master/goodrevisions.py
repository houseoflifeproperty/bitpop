# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""A StatusReceiver module to store good revision numbers on a specific server.

The GoodRevisions class can be given a dictionary of builders to a set
of critical steps to validate before storing the revision number.
"""

import urllib

from buildbot.status.builder import FAILURE
from buildbot.status import base
from twisted.python import log

from master import build_utils
from master import get_password


class GoodRevisions(base.StatusReceiverMultiService):
  """This is a status notifier which stores good revision numbers."""

  def __init__(self, store_revisions_url, good_revision_steps=None,
               use_getname=False, check_revisions=True):
    """Constructor with following specific arguments.

    @type good_revision_steps: Dictionary of builder name string mapped to a
                               list of step strings.
    @param good_revision_steps: The list of all the steps of all the builders
                                we want to validate before storing this
                                revision as good.
    @param store_revisions_url: URL where revision info is stored.a

    @type check_revisions: Boolean, default to True.
    @param check_revisions: Check revisions and users for closing the tree.
    """
    base.StatusReceiverMultiService.__init__(self)
    self.good_revision_steps = good_revision_steps or {}
    self.store_revisions_url = store_revisions_url
    # TODO(maruel): Enforce use_getname == True
    self.use_getname = use_getname
    self.check_revisions = check_revisions

    # We remember the success of interesting steps in a dictionary index by the
    # revision number. As soon as one of the interesting steps fail we flush
    # the revision for which we failed. We also flush the revision as soon as we
    # have seen a success for all the steps in good_revision_steps for that
    # revision (or any more recent revision). And finally, we don't need to add
    # information for a revision that is lower than the last known good
    # revision described below.
    self.succeeded_steps = {}

    # List of failed revisions so that we don't try to remember subsequent step
    # success for that revision for nothing. And again, we don't need to add
    # information for a revision that is lower than the last known good
    # revision described below.
    self.failed_revisions = []

    # To identify revisions lower than this one as not interesting.
    self.last_known_good_revision = 0

    # The status object we must subscribe to.
    self.status = None
    self.password = get_password.Password('.status_password').GetPassword()

  def setServiceParent(self, parent):
    base.StatusReceiverMultiService.setServiceParent(self, parent)
    self.setup()

  def setup(self):
    # pylint: disable=E1101
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

  def disownServiceParent(self):
    self.status.unsubscribe(self)
    # pylint: disable=E1101
    for w in self.watched:
      w.unsubscribe(self)
    return base.StatusReceiverMultiService.disownServiceParent(self)

  def getInterestingBuilders(self):
    if not self.good_revision_steps:
      return self.status.getBuilderNames()
    return self.good_revision_steps.keys()

  def getInterestingBuildSteps(self, builder_name, build):
    if (not self.good_revision_steps or
        (builder_name in self.good_revision_steps and
          not self.good_revision_steps[builder_name])):
      # All builders are interesting, or all steps for this builder are
      # interesting.
      if self.use_getname:
        return [step.getName() for step in build.getSteps()]
      else:
        return [step.getText()[0] for step in build.getSteps()]

    return self.good_revision_steps[builder_name]

  def isInterestingBuilder(self, name):
    return name in self.getInterestingBuilders()

  def isInterestingBuildStep(self, builder_name, build, step_text):
    return step_text in self.getInterestingBuildSteps(builder_name, build)

  def builderAdded(self, name, builder):
    # Only subscribe to builders we are interested in.
    if self.isInterestingBuilder(name):
      return self

  def buildStarted(self, name, build):
    """A build has started allowing us to register for stepFinished."""
    if self.isInterestingBuilder(name):
      return self

  def stepFinished(self, build, step, results):
    """A build step has just finished."""
    builder_name = build.getBuilder().getName()

    # For some reason we sometimes get called even if we didn't subscribe.
    if not self.isInterestingBuilder(builder_name):
      log.msg('Was called for %s even if not subscribed' % builder_name)
      return

    if self.use_getname:
      step_text = step.getName()
    else:
      step_text = step.getText()[0]
    # We only need to deal with interesting steps.
    if not self.isInterestingBuildStep(builder_name, build, step_text):
      log.msg('not interested in step %s' % step_text)
      return

    # TODO(maruel): Support git.
    latest_revision = build_utils.getLatestRevision(build)
    if not latest_revision:
      log.msg('no lastest revision for build %s' % build.asDict())
      return

    # If check_revisions=False that means that the tree closure request is
    # coming from nightly scheduled bots or a git poller, that need not
    # necessarily have the revision info or the revision is a hash that cannot
    # be compared.
    if self.check_revisions:
      latest_revision = int(latest_revision)

      # If we already succeeded for a more recent revision,
      # let's just forget about this one.
      if latest_revision <= self.last_known_good_revision:
        log.msg('revision too old')
        return

    # If we already failed for this revision,
    # there is nothing else we need to do.
    if latest_revision in self.failed_revisions:
      assert latest_revision not in self.succeeded_steps
      log.msg('revision already failed')
      return

    # If we have failed, we add this revision to our failure list and flush it
    # from the success dict, if it is there. We also store it on the status
    # server.
    if results[0] == FAILURE:
      log.msg('%s is a failed revision.' % str(latest_revision))
      self.failed_revisions.append(latest_revision)
      # pop() with a default value allows us to remove an element
      # without having to test if it is there in the first place.
      self.succeeded_steps.pop(latest_revision, None)
      self.PostData(revision=latest_revision, success=0,
                    steps_text=step.getText())
      return

    # Now let's add the succeeded steps to our success dict.
    self.succeeded_steps.setdefault(latest_revision, {})
    revision_status = self.succeeded_steps[latest_revision]
    revision_status.setdefault(builder_name, [])
    revision_status[builder_name].append(step_text)

    # We must complete all the requested steps for all builds, before we can
    # store this revision as a successful one and then forget about all
    # previous revisions info.
    for builder in self.getInterestingBuilders():
      if builder not in revision_status:
        log.msg('Still missing builder %s to declare %s a good revision' %
                (builder, str(latest_revision)))
        return
      succeeded_steps = revision_status[builder]
      for required_step in self.getInterestingBuildSteps(builder, build):
        if required_step not in succeeded_steps:
          log.msg('Still missing step %s\%s to declare %s a good revision' %
                  (builder, required_step, str(latest_revision)))
          return

    # Start by remembering this success.
    log.msg('Found LKGR = %s' % latest_revision)
    self.last_known_good_revision = latest_revision

    # Store it on the status server.
    self.PostData(revision=latest_revision, success=1)

    if self.check_revisions:
      # And now cleanup residual information from earlier revisions
      # Iterate through a list of keys to allow removal while we iterate.
      for revision in list(self.succeeded_steps.keys()):
        if revision <= latest_revision:
          del self.succeeded_steps[revision]
      for revision in self.failed_revisions:
        assert revision != latest_revision
        if revision < latest_revision:
          self.failed_revisions.remove(revision)
    else:
      # TODO(maruel): Use LRU discarding. Right now it's a memory leak.
      pass

  def PostData(self, revision, success, steps_text=None):
    """Post the revision data to the server store."""
    params = {
      'revision': revision,
      'success': success,
      'password': self.password,
    }
    if steps_text:
      params['steps'] = ", ".join(steps_text)
    log.msg('Sending this lkgr info: %s' % str(params))
    request = urllib.urlopen(self.store_revisions_url, urllib.urlencode(params))
    request.close()
