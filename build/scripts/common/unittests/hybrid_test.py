#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in hybrid.py."""

import unittest

import test_env  # pylint: disable=W0611

import common.hybrid as hybrid

from twisted.internet import defer
from twisted.trial import unittest as twisted_unittest


@hybrid.inlineCallbacks
def reflector(value):
  hybrid.returnValue(value)
  yield

@hybrid.inlineCallbacks
def doubler(value):
  a = yield reflector(value)
  b = yield reflector(value)
  hybrid.returnValue(a + b)

@hybrid.inlineCallbacks
def standaloneHybrid(a, b=0, c=0):
  result = yield doubler(a)
  result += yield doubler(b)
  result += yield doubler(c)
  hybrid.returnValue(result)

class TestBaseClass(object):

  def __init__(self, base):
    self.base = base

  @staticmethod
  def clean(v):
    return v

  @hybrid.inlineCallbacks
  def inner(self, v):
    v = self.clean(self.base * v)
    hybrid.returnValue(v)
    yield

  @hybrid.inlineCallbacks
  def outer(self, a, b):
    a = yield self.inner(a)
    b = yield self.inner(b)
    hybrid.returnValue(a + b)

  def regularFunction(self, a, b):
    return self.outer(a, b)


class SynchronousTestClass(TestBaseClass, hybrid.Synchronous.MixIn):
  pass

class TwistedTestClass(TestBaseClass, hybrid.Twisted.MixIn):
  pass


class SynchronousTestCase(unittest.TestCase):

  def testLeafCall(self):
    self.assertEqual(
        hybrid.Synchronous.call(reflector)(10),
        10
    )

  def testNestedCall(self):
    self.assertEqual(
        hybrid.Synchronous.call(standaloneHybrid)(
            10,
            c=20,
        ),
        60
    )


class SynchronousMixInTestCase(twisted_unittest.TestCase):

  def setUp(self):
    self.c = SynchronousTestClass(2)

  def testRegularFunctionCall(self):
    self.assertEqual(
        self.c.regularFunction(10, 20),
        60
    )

  def testInnerCall(self):
    self.assertEqual(
        self.c.inner(10),
        20
    )

  def testOuterCall(self):
    self.assertEqual(
        self.c.outer(10, 20),
        60
    )


class TwistedTestCase(twisted_unittest.TestCase):

  def testLeafCall(self):
    d = hybrid.Twisted.call(reflector)(10)

    def check(result):
      self.assertEqual(result, 10)
    d.addCallback(check)
    return d

  @defer.inlineCallbacks
  def testNestedCall(self):
    result = yield hybrid.Twisted.call(standaloneHybrid)(
        10,
        c=20,
    )
    self.assertEqual(result, 60)

  def testIndirectNestedCall(self):
    d = defer.succeed(10)
    d.addCallback(
        hybrid.Twisted.call(standaloneHybrid),
        20, # (b)
        c=40)

    def check(result):
      self.assertEqual(result, 140)
    d.addCallback(check)

    return d


class TwistedMixInTestCase(twisted_unittest.TestCase):

  def setUp(self):
    self.c = TwistedTestClass(2)

  def testRegularFunctionCall(self):
    d = self.c.regularFunction(10, 20)

    def check(value):
      self.assertEqual(value, 60)
    d.addCallback(check)
    return d

  def testInnerCall(self):
    d = self.c.inner(10)

    def check(value):
      self.assertEqual(value, 20)
    d.addCallback(check)
    return d

  def testOuterCall(self):
    d = self.c.outer(10, 20)

    def check(value):
      self.assertEqual(value, 60)
    d.addCallback(check)
    return d


if __name__ == '__main__':
  unittest.main()
