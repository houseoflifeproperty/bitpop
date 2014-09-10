#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Collection of unit tests for 'common.frozendict' library.
"""

import copy
import unittest

import test_env  # pylint: disable=W0611

from common.frozendict import frozendict

class FunctionTestCase(unittest.TestCase):

  def testTupleInstantiation(self):
    self.assertEqual(
        frozendict((('a', 1), ('b', 2))),
        {'a': 1, 'b': 2,}
    )

  def testKwargInstantiation(self):
    self.assertEqual(
        frozendict(a=1, b=2),
        {'a': 1, 'b': 2,}
    )

  def testImmutable(self):
    frozen = frozendict(a=1, b=2)

    def assign():
      frozen['b'] = 0
    self.assertRaises(
        TypeError,
        assign
    )

    def delete():
      del(frozen['b'])
    self.assertRaises(
        TypeError,
        delete
    )

    def assignNew():
      frozen['c'] = 3
    self.assertRaises(
        TypeError,
        assignNew
    )


  def testEquality(self):
    self.assertEqual(
        frozendict(a=1, b=2),
        frozendict(a=1, b=2),
    )

    self.assertNotEqual(
        frozendict(a=1),
        frozendict(a=1, b=2),
    )

  def testDictEquality(self):
    self.assertEqual(
        frozendict(a=1, b=2),
        {'a': 1, 'b': 2,},
    )

    self.assertNotEqual(
        frozendict(a=1),
        {'a': 1, 'b': 2,},
    )

  def testItemTuple(self):
    self.assertEqual(
        frozendict().itemtuple(),
        ()
    )

    self.assertEqual(
        frozendict(a=1, b=2).itemtuple(),
        (('a', 1), ('b', 2))
    )

  def testDeepCopy(self):
    frozen = frozendict(a=1, b=2)
    cpy = copy.deepcopy(frozen)

    # Copy is regular 'dict'
    self.assertIs(
        type(cpy),
        dict
    )

    # Copy should equal the original contents
    self.assertEqual(
        cpy,
        frozen
    )

  def testDeepCopyRecursive(self):
    frozen = frozendict(a=1, b=frozendict(x=1, y=2))
    cpy = copy.deepcopy(frozen)

    # All 'frozendict' should be 'dict'
    self.assertIs(
        type(cpy),
        dict
    )
    self.assertIs(
        type(cpy['b']),
        dict
    )

    # Copy should equal the original contents
    self.assertEqual(
        cpy,
        frozen
    )

  def testMutableDict(self):
    frozen = frozendict(a=1, b=frozendict(x=1, y=2))
    mutable = frozen.mutableDict()

    # Copy should equal the original contents
    self.assertEqual(
        mutable,
        frozen
    )

    # All 'frozendict' must be mutable
    try:
      mutable['c'] = 10
    except TypeError:
      self.fail("Failed to assign to mutable copy")
    self.assertEqual(
        mutable,
        {'a': 1, 'b': {'x': 1, 'y': 2}, 'c': 10}
    )

    try:
      mutable['b']['z'] = 20
    except TypeError:
      self.fail("Failed to assign to mutable subcopy")
    self.assertEqual(
        mutable,
        {'a': 1, 'b': {'x': 1, 'y': 2, 'z': 20}, 'c': 10}
    )

  def testExtend(self):
    frozen = frozendict(a=1, b=2)
    ext = frozen.extend(c=3)
    self.assertEqual(
        type(ext),
        frozendict
    )
    self.assertEqual(
        ext,
        {'a': 1, 'b': 2, 'c': 3}
    )

  def testExtendReplace(self):
    frozen = frozendict(a=1, b=2)
    ext = frozen.extend(b=10, c=3)
    self.assertEqual(
        ext,
        {'a': 1, 'b': 10, 'c': 3}
    )

  def testDictKey(self):
    d = {
        frozendict(a=1, b=2): 1,
        'b': 2,
    }

    self.assertEqual(
        d[frozendict(a=1, b=2)],
        1
    )


if __name__ == '__main__':
  unittest.main()
