#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Collection of unit tests for 'common.memo' library.
"""

import unittest

import test_env  # pylint: disable=W0611

from common import memo

class MemoTestCase(unittest.TestCase):

  def setUp(self):
    self.tagged = set()

  def tag(self, tag=None):
    self.assertNotIn(tag, self.tagged)
    self.tagged.add(tag)

  def assertTagged(self, *tags):
    if len(tags) == 0:
      tags = (None,)
    self.assertEqual(set(tags), self.tagged)

  def clearTagged(self):
    self.tagged.clear()


class FunctionTestCase(MemoTestCase):

  def testFuncNoArgs(self):
    @memo.memo()
    def func():
      self.tag()
      return 'foo'

    for _ in xrange(10):
      self.assertEqual(func(), 'foo')
    self.assertTagged()

  def testFuncAllArgs(self):
    @memo.memo()
    def func(a, b):
      self.tag((a, b))
      return (a + b)

    # Execute multiple rounds of two unique function executions.
    for _ in xrange(10):
      self.assertEqual(func(1, 2), 3)
      self.assertEqual(func(3, 4), 7)
    self.assertTagged(
        (1, 2),
        (3, 4),
    )

  def testFuncIgnoreArgs(self):
    @memo.memo(ignore=('b'))
    def func(a, b):
      self.tag(a)
      return (a + b)

    # Execute multiple rounds of two unique function executions.
    for _ in xrange(10):
      self.assertEqual(func(1, 1), 2)
      self.assertEqual(func(1, 2), 2)
      self.assertEqual(func(2, 1), 3)
      self.assertEqual(func(2, 2), 3)
    self.assertTagged(
        1,
        2,
    )

  def testOldClassMethod(self):
    class Test:
      # Disable 'no __init__ method' warning | pylint: disable=W0232

      @classmethod
      @memo.memo()
      def func(cls, a):
        self.tag(a)
        return a

    # Execute multiple rounds of two unique function executions.
    for _ in xrange(10):
      self.assertEqual(Test.func(1), 1)
      self.assertEqual(Test.func(2), 2)
    self.assertTagged(
        1,
        2,
    )

  def testNewClassMethod(self):
    class Test(object):
      # Disable 'no __init__ method' warning | pylint: disable=W0232

      @classmethod
      @memo.memo()
      def func(cls, a):
        self.tag(a)
        return a

    # Execute multiple rounds of two unique function executions.
    for _ in xrange(10):
      self.assertEqual(Test.func(1), 1)
      self.assertEqual(Test.func(2), 2)
    self.assertTagged(
        1,
        2,
    )

  def testOldClassStaticMethod(self):
    class Test:
      # Disable 'no __init__ method' warning | pylint: disable=W0232

      @staticmethod
      @memo.memo()
      def func(a):
        self.tag(a)
        return a

    # Execute multiple rounds of two unique function executions.
    for _ in xrange(10):
      self.assertEqual(Test.func(1), 1)
      self.assertEqual(Test.func(2), 2)
    self.assertTagged(
        1,
        2,
    )

  def testNewClassStaticMethod(self):
    class Test(object):
      # Disable 'no __init__ method' warning | pylint: disable=W0232

      @staticmethod
      @memo.memo()
      def func(a):
        self.tag(a)
        return a

    # Execute multiple rounds of two unique function executions.
    for _ in xrange(10):
      self.assertEqual(Test.func(1), 1)
      self.assertEqual(Test.func(2), 2)
    self.assertTagged(
        1,
        2,
    )

  def testClearAllArgs(self):
    @memo.memo()
    def func(a, b=10):
      self.tag((a, b))
      return (a + b)

    # First round
    self.assertEqual(func(1), 11)
    self.assertEqual(func(1, b=0), 1)
    self.assertTagged(
        (1, 10),
        (1, 0),
    )

    # Clear (1)
    self.clearTagged()
    func.memo_clear(1)

    self.assertEqual(func(1), 11)
    self.assertEqual(func(1, b=0), 1)
    self.assertTagged(
        (1, 10),
    )

    # Clear (1, b=0)
    self.clearTagged()
    func.memo_clear(1, b=0)

    self.assertEqual(func(1), 11)
    self.assertEqual(func(1, b=0), 1)
    self.assertTagged(
        (1, 0),
    )


class MemoInstanceMethodTestCase(MemoTestCase):

  class TestBaseOld:
    def __init__(self, test_case, name):
      self.test_case = test_case
      self.name = name

    def __hash__(self):
      # Prevent this instance from being used as a memo key
      raise NotImplementedError()


  class TestBaseNew:
    def __init__(self, test_case, name):
      self.test_case = test_case
      self.name = name

    def __hash__(self):
      # Prevent this instance from being used as a memo key
      raise NotImplementedError()


  class TestHash(object):

    @memo.memo_i()
    def __hash__(self):
      return 0


  def testOldClassNoArgs(self):
    class Test(self.TestBaseOld):
      # Disable 'hash not overridden' warning | pylint: disable=W0223

      @memo.memo_i()
      def func(self):
        self.test_case.tag(self.name)
        return 'foo'

    t0 = Test(self, 't0')
    t1 = Test(self, 't1')
    for _ in xrange(10):
      self.assertEqual(t0.func(), 'foo')
      self.assertEqual(t1.func(), 'foo')
    self.assertTagged(
        't0',
        't1',
    )

  def testNewClassNoArgs(self):
    class Test(self.TestBaseNew):
      # Disable 'hash not overridden' warning | pylint: disable=W0223

      @memo.memo_i()
      def func(self):
        self.test_case.tag(self.name)
        return 'foo'

    t0 = Test(self, 't0')
    t1 = Test(self, 't1')
    for _ in xrange(10):
      self.assertEqual(t0.func(), 'foo')
      self.assertEqual(t1.func(), 'foo')
    self.assertTagged(
        't0',
        't1',
    )

  def testOldClassArgs(self):
    class Test(self.TestBaseOld):
      # Disable 'hash not overridden' warning | pylint: disable=W0223

      @memo.memo_i()
      def func(self, a, b):
        self.test_case.tag((self.name, a, b))
        return (a + b)

    t0 = Test(self, 't0')
    t1 = Test(self, 't1')
    for _ in xrange(10):
      self.assertEqual(t0.func(1, 2), 3)
      self.assertEqual(t0.func(1, 3), 4)
      self.assertEqual(t1.func(1, 2), 3)
      self.assertEqual(t1.func(1, 3), 4)
    self.assertTagged(
        ('t0', 1, 2),
        ('t0', 1, 3),
        ('t1', 1, 2),
        ('t1', 1, 3),
    )

  def testNewClassArgs(self):
    class Test(self.TestBaseNew):
      # Disable 'hash not overridden' warning | pylint: disable=W0223

      @memo.memo_i()
      def func(self, a, b):
        self.test_case.tag((self.name, a, b))
        return (a + b)

    t0 = Test(self, 't0')
    t1 = Test(self, 't1')
    for _ in xrange(10):
      self.assertEqual(t0.func(1, 2), 3)
      self.assertEqual(t0.func(1, 3), 4)
      self.assertEqual(t1.func(1, 2), 3)
      self.assertEqual(t1.func(1, 3), 4)
    self.assertTagged(
        ('t0', 1, 2),
        ('t0', 1, 3),
        ('t1', 1, 2),
        ('t1', 1, 3),
    )

  def testClear(self):
    class Test(self.TestBaseNew):
      # Disable 'hash not overridden' warning | pylint: disable=W0223

      @memo.memo_i()
      def func(self, a):
        self.test_case.tag((self.name, a))
        return a

    # Call '10' and '20'
    t = Test(self, 'test')
    t.func(10)
    self.assertTagged(
        ('test', 10),
    )

    # Clear
    self.clearTagged()
    t.func.memo_clear(10)

    # Call '10'; it should be tagged
    t.func(10)
    self.assertTagged(
        ('test', 10),
    )


  def testOverrideHash(self):
    self.assertEquals(hash(self.TestHash()), 0)


class MemoClassMethodTestCase(MemoTestCase):
  """Tests handling of the 'cls' and 'self' parameters"""

  class Test(object):

    def __init__(self, test_case, name):
      self.test_case = test_case
      self.name = name

    @memo.memo()
    def func(self, a):
      self.test_case.tag(self.name)
      return a

    @classmethod
    @memo.memo(ignore=('test_case', 'tag'))
    def class_func(cls, a, test_case):
      test_case.tag(a)
      return a


  class TestWithEquals(Test):

    def __hash__(self):
      return hash(type(self))

    def __eq__(self, other):
      return type(other) == type(self)


  def testClassMethodNoEquals(self):
    self.assertEqual(self.Test.class_func(1, self), 1)
    self.assertEqual(self.Test.class_func(2, self), 2)
    self.assertTagged(
        1,
        2,
    )

  def testInstanceMethodNoEquals(self):
    t0 = self.Test(self, 't0')
    t1 = self.Test(self, 't1')

    self.assertEqual(t0.func(1), 1)
    self.assertEqual(t1.func(1), 1)
    self.assertTagged(
        't0',
        't1',
    )

  def testInstanceMethodWithEquals(self):
    t0 = self.TestWithEquals(self, 't0')
    t1 = self.TestWithEquals(self, 't1')

    self.assertEqual(t0.func(1), 1)
    self.assertEqual(t1.func(1), 1)
    self.assertTagged(
        't0',
    )


if __name__ == '__main__':
  unittest.main()
