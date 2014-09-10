#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for gatekeeper testcases."""

import unittest

import test_env  # pylint: disable=W0611
from common import find_depot_tools  # pylint: disable=W0611

from buildbot.status.results import FAILURE
import mock
from twisted.internet import defer

from testing_support import auto_stub

from master import gatekeeper

# Mocks confuse pylint.
# pylint: disable=E1101


class FakePassword(object):
  def __init__(self, _):
    pass

  @staticmethod
  def GetPassword():
    return 'testpw'


def _get_master_status():
  ms = mock.Mock()
  ms.getTitle.return_value = 'Fake master'
  ms.getBuildbotURL.return_value = 'http://somewhere'
  ms.getSlaveNames.return_value = ['slave1', 'slave2']
  return ms


def _get_gatekeeper(tree_status_url, mock_interesting, branches=None):
  """Returns a partially mocked GateKeeper instance."""
  mn = gatekeeper.GateKeeper(
      tree_status_url,
      fromaddr='from@example.org',
      mode='all',
      builders=['builder1'],
      branches=branches,
      use_getname=True,
      lookup=None)
  mn.master_status = _get_master_status()
  # Nuke out sending emails.
  mn.sendmail = mock.Mock()
  mn.sendmail.return_value = 'email sent!'
  if mock_interesting:
    mn.isInterestingStep = mock.Mock()
    mn.isInterestingStep.return_value = True
    mn.getFinishedMessage = mock.Mock()
  return mn


def _get_build():
  """Returns a buildbot.status.build.BuildStatus."""
  # buildbot.status.builder.BuilderStatus
  builder = mock.Mock()
  builder.getName.return_value = 'builder1'

  change = mock.Mock()
  change.asHTML.return_value = '<change1>'

  build = mock.Mock()
  build.getBuilder.return_value = builder
  build.getResponsibleUsers.return_value = ['joe']
  build.getChanges.return_value = [change]
  return build


def _get_step():
  """Returns a buildbot.status.buildstep.BuildStepStatus."""
  step = mock.Mock()
  step.getName.return_value = 'step1'
  return step


class GateKeeperTest(auto_stub.TestCase):
  def setUp(self):
    super(GateKeeperTest, self).setUp()
    self.mock(gatekeeper.client, 'getPage', mock.Mock())
    self.mock(gatekeeper.get_password, 'Password', FakePassword)
    self.mock(gatekeeper.build_utils, 'getAllRevisions', mock.Mock())
    self.mock(gatekeeper.build_utils, 'EmailableBuildTable', mock.Mock())
    gatekeeper.build_utils.getAllRevisions.return_value = [23]
    gatekeeper.build_utils.EmailableBuildTable.return_value = 'end of table'

  def _check(self, email_sent, tree_status_url='url'):
    # Verify that an email was sent or not, as expected.
    mn = _get_gatekeeper(tree_status_url=tree_status_url, mock_interesting=True)
    build = _get_build()
    step = _get_step()

    # Trigger the code
    d = mn.stepFinished(build, step, [FAILURE])

    self.assertTrue(isinstance(d, defer.Deferred))
    mn.isInterestingStep.assert_called_once_with(build, step, [FAILURE])
    if tree_status_url:
      gatekeeper.client.getPage.assert_called_once_with('url', agent='buildbot')
    else:
      self.assertEquals(0, gatekeeper.client.getPage.call_count)
    if email_sent:
      self.assertEquals(1, mn.sendmail.call_count)
      mn.getFinishedMessage.assert_called_once_with(
          'email sent!', 'builder1', build, 'step1')
    else:
      self.assertEquals(0, mn.sendmail.call_count)
      self.assertEquals(0, mn.getFinishedMessage.call_count)

  def test_Creation(self):
    notifier = gatekeeper.GateKeeper(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.',
        tree_status_url='http://localhost/')
    self.assertTrue(notifier)

  def test_branchname_mismatch(self):
    mn = _get_gatekeeper(tree_status_url='url',
                         mock_interesting=False,
                         branches=['bar'])
    build = _get_build()
    build.getProperty.return_value = 'foo'
    step = _get_step()
    self.assertFalse(mn.isInterestingStep(build, step, [FAILURE]))

  def test_branchname_match(self):
    mn = _get_gatekeeper(tree_status_url='url',
                         mock_interesting=False,
                         branches=['foo'])
    build = _get_build()
    build.getProperty.return_value = 'foo'
    build.getPreviousBuild.return_value = None
    step = _get_step()
    self.assertTrue(mn.isInterestingStep(build, step, [FAILURE]))

  def test_buildMessage(self):
    # Make sure the code flows up to buildMessage with isInterestingStep mocked
    # out.
    mn = _get_gatekeeper('url', True)
    mn.buildMessage = mock.Mock()
    build = _get_build()
    step = _get_step()

    mn.stepFinished(build, step, [FAILURE])
    mn.buildMessage.assert_called_with('builder1', build, [FAILURE], 'step1')
    mn.isInterestingStep.assert_called_once_with(build, step, [FAILURE])
    self.assertEquals(0, mn.sendmail.call_count)

  def test_tree_open(self):
    # Tree is open.
    gatekeeper.client.getPage.return_value = defer.succeed('1')
    self._check(True)

  def test_tree_closed(self):
    # Tree is closed.
    gatekeeper.client.getPage.return_value = defer.succeed('0')
    self._check(False)

  def test_url_fetch_fail(self):
    # Tree fetch failed.
    gatekeeper.client.getPage.return_value = defer.fail(IOError())
    self._check(True)

  def test_no_url(self):
    # An email is still sent if no url.
    self._check(True, None)


if __name__ == '__main__':
  unittest.main()
