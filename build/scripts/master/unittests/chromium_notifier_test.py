#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_notifier testcases."""

import unittest

import test_env  # pylint: disable=W0611

from buildbot.status.builder import FAILURE
import mock

from master import chromium_notifier


class ChromiumNotifierTest(unittest.TestCase):

  class fakeStep():
    def __init__(self, name, text=None):
      self.name = name
      self.text = text

    def getName(self):
      return self.name

    def getText(self):
      return self.text

  def testChromiumNotifierCreation(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.')
    self.assertTrue(notifier)

  def testChromiumNotifierWildcard(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        categories_steps={'foo': '*'},
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        use_getname=True,
        status_header='Failure on test.')
    self.assertTrue(notifier)
    builder_status = mock.Mock()
    builder_status.getName.return_value = 'foo'
    builder_status.category = 'foo|test'
    build_status = mock.Mock()
    build_status.getBuilder.return_value = builder_status
    step_status = mock.Mock()
    step_status.getName.return_value = 'bar'
    results = [FAILURE]
    notifier.buildMessage = mock.Mock()
    notifier.buildMessage.return_value = True
    retval = notifier.stepFinished(build_status, step_status, results)
    self.assertTrue(retval)

  def testChromiumNotifierSingleMatch(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        categories_steps={'foo': ['bar']},
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        use_getname=True,
        status_header='Failure on test.')
    self.assertTrue(notifier)
    builder_status = mock.Mock()
    builder_status.getName.return_value = 'foo'
    builder_status.category = 'foo|test'
    build_status = mock.Mock()
    build_status.getBuilder.return_value = builder_status
    step_status = mock.Mock()
    step_status.getName.return_value = 'bar'
    results = [FAILURE]
    notifier.buildMessage = mock.Mock()
    notifier.buildMessage.return_value = True
    retval = notifier.stepFinished(build_status, step_status, results)
    self.assertTrue(retval)

  def testChromiumNotifierWildcardNoBuilderMatch(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        categories_steps={'foobar': '*'},
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        use_getname=True,
        status_header='Failure on test.')
    self.assertTrue(notifier)
    builder_status = mock.Mock()
    builder_status.getName.return_value = 'foo'
    builder_status.category = 'foo|test'
    build_status = mock.Mock()
    build_status.getBuilder.return_value = builder_status
    step_status = mock.Mock()
    step_status.getName.return_value = 'bar'
    results = [FAILURE]
    notifier.buildMessage = mock.Mock()
    notifier.buildMessage.return_value = True
    retval = notifier.stepFinished(build_status, step_status, results)
    self.assertEquals(retval, None)

  def testChromiumNotifierDecoration(self):
    notifier = chromium_notifier.ChromiumNotifier(
        fromaddr='buildbot@test',
        mode='failing',
        forgiving_steps=[],
        lookup='test',
        sendToInterestedUsers=False,
        extraRecipients=['extra@test'],
        status_header='Failure on test.')
    self.assertEquals(notifier.getGenericName("foo"), "foo")
    self.assertEquals(notifier.getGenericName("foo "), "foo")
    self.assertEquals(notifier.getGenericName(" foo"), "foo")
    self.assertEquals(notifier.getGenericName("foo [bar]"), "foo")
    self.assertEquals(notifier.getGenericName(" foo [bar]"), "foo")
    self.assertEquals(notifier.getGenericName("f [u] [bar]"), "f [u]")
    self.assertEquals(notifier.getGenericName("foo[bar]"), "foo")
    self.assertEquals(notifier.getGenericName("[foobar]"), "[foobar]")
    self.assertEquals(notifier.getGenericName(" [foobar]"), "[foobar]")
    self.assertEquals(notifier.getGenericName(" [foobar] "), "[foobar]")
    self.assertEquals(notifier.getGenericName("[foobar] [foo]"), "[foobar]")
    self.assertEquals(notifier.getGenericName("apple ]["), "apple ][")
    self.assertEquals(notifier.getGenericName("ipad ][][]["), "ipad ][][][")
    self.assertEquals(notifier.getGenericName("ipad [][]"), "ipad []")
    self.assertEquals(notifier.getGenericName("box []"), "box")


if __name__ == '__main__':
  unittest.main()
