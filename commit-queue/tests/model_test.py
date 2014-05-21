#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for model.py."""

import json
import logging
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))
from model import PersistentMixIn, TYPE_FLAG


# Used a marker to determine that the check must ignore the value.
IGNORE = object()


def _members(instance):
  return sorted(i for i in dir(instance) if not i.startswith('_'))


class Empty(PersistentMixIn):
  pass


class Basic(PersistentMixIn):
  a = int
  b = float

  def test_me(self):
    return self.a + 1


class Inner(PersistentMixIn):
  c = Basic
  d = unicode


class Subclass(Inner):
  e = list


class MultiValue(PersistentMixIn):
  f = (None, bool)
  g = (unicode, float)


class WithInit(PersistentMixIn):
  h = unicode
  def __init__(self):
    # The values are overriden when loaded.
    super(WithInit, self).__init__(h=u'baz')
    # i is not serialized.
    self.i = 3


class NotType(PersistentMixIn):
  j = set
  # k is not a type so it's not serialized.
  k = 23


class TypeOrDict(PersistentMixIn):
  # Accepts a Basic or a dict.
  l = (Basic, dict)


class StrDisallowed(PersistentMixIn):
  m = str


def marshall(data):
  """JSON encodes then decodes to make sure the data has passed through JSON
  type reduction.
  """
  return json.loads(json.dumps(data))


class Base(unittest.TestCase):
  def _check(self, actual, expected_type, **kwargs):
    kwargs['as_dict'] = IGNORE
    kwargs['from_dict'] = IGNORE
    self.assertEqual(expected_type, type(actual))
    self.assertEqual(sorted(kwargs), _members(actual))
    for member in sorted(kwargs):
      expected = kwargs[member]
      if expected == IGNORE:
        continue
      self.assertEqual(expected, getattr(actual, member))


class Serialize(Base):
  def testEmpty(self):
    expected = {
      TYPE_FLAG: 'Empty',
    }
    self.assertEqual(expected, Empty().as_dict())

  def testBasic(self):
    data = Basic(b=23.2)
    expected = {
        'a': 0,
        'b': 23.2,
        TYPE_FLAG: 'Basic',
    }
    self.assertEqual(expected, data.as_dict())

  def testBasicFailConstruct(self):
    # TODO(maruel): should int be auto-upgraded to float when requested?
    self.assertRaises(TypeError, Basic, b=23)

  def testBasicFailAsDict(self):
    # TODO(maruel): should int be auto-upgraded to float when requested?
    data = Basic()
    data.b = 23
    self.assertRaises(TypeError, data.as_dict)

  def testInner(self):
    data = Inner(c=Basic(a=21, b=23.2), d=u'foo')
    expected = {
      'c': {
        'a': 21,
        'b': 23.2,
        TYPE_FLAG: 'Basic',
      },
      TYPE_FLAG: 'Inner',
      'd': 'foo',
    }
    self.assertEqual(expected, data.as_dict())

  def testSubclass(self):
    data = Subclass(c=Basic(a=23), e=[Basic(), {'random': 'stuff', 'x': True}])
    expected = {
      'c': {
          'a': 23,
          'b': 0.,
          TYPE_FLAG: 'Basic',
      },
      'e': [
        {
          'a': 0,
          'b': 0.,
          TYPE_FLAG: 'Basic',
        },
        {
          'random': 'stuff',
          'x': True,
        },
      ],
      'd': '',
      TYPE_FLAG: 'Subclass',
    }
    self.assertEqual(expected, data.as_dict())

  def testMultiValue_default(self):
    data = MultiValue()
    expected = {
      'f': None,
      'g': '',
      TYPE_FLAG: 'MultiValue',
    }
    self.assertEqual(expected, data.as_dict())

  def testMultiValue_first(self):
    data = MultiValue(f=None, g=u'foo')
    expected = {
      'f': None,
      'g': 'foo',
      TYPE_FLAG: 'MultiValue',
    }
    self.assertEqual(expected, data.as_dict())

  def testMultiValue_second(self):
    data = MultiValue(f=False, g=3.1)
    expected = {
      'f': False,
      'g': 3.1,
      TYPE_FLAG: 'MultiValue',
    }
    self.assertEqual(expected, data.as_dict())

  def testWithInit(self):
    data = WithInit()
    self._check(data, WithInit, h='baz', i=3)
    expected = {
      'h': 'baz',
      TYPE_FLAG: 'WithInit',
    }
    self.assertEqual(expected, data.as_dict())

  def testNotType(self):
    data = NotType()
    self._check(data, NotType, j=set(), k=23)
    expected = {
      'j': [],
      TYPE_FLAG: 'NotType',
    }
    self.assertEqual(expected, data.as_dict())

  def testTypeOrDict_Basic(self):
    data = TypeOrDict()
    self._check(data, TypeOrDict, l=IGNORE)
    self._check(data.l, Basic, a=0, b=0., test_me=IGNORE)
    expected = {
      'l': {
        'a': 0,
        'b': 0.0,
        TYPE_FLAG: 'Basic',
      },
      TYPE_FLAG: 'TypeOrDict',
    }
    self.assertEqual(expected, data.as_dict())

  def testTypeOrDict_dict(self):
    data = TypeOrDict(l={'foo': u'bar'})
    self._check(data, TypeOrDict, l={'foo': u'bar'})
    expected = {
      'l': {
        'foo': 'bar',
      },
      TYPE_FLAG: 'TypeOrDict',
    }
    self.assertEqual(expected, data.as_dict())

  def testStrDisallowed(self):
    self.assertRaises(TypeError, StrDisallowed)


class Deserialize(Base):
  def testNotFound(self):
    data = { TYPE_FLAG: 'DoesNotExists' }
    self.assertRaises(KeyError, PersistentMixIn.from_dict, marshall(data))

  def testEmpty(self):
    data = { }
    self.assertRaises(KeyError, PersistentMixIn.from_dict, marshall(data))

  def testBasic(self):
    data = {
        'a': 22,
        'b': 23.2,
        TYPE_FLAG: 'Basic',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, Basic, a=22, b=23.2, test_me=IGNORE)

  def testBasic_WrongType(self):
    data = {
        'a': None,
        TYPE_FLAG: 'Basic',
    }
    self.assertRaises(TypeError, PersistentMixIn.from_dict, marshall(data))

  def testInner(self):
    data = {
      'c': {
        'a': 42,
        'b': .1,
        TYPE_FLAG: 'Basic',
      },
      TYPE_FLAG: 'Inner',
      'd': 'foo2',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, Inner, c=IGNORE, d='foo2')
    self._check(actual.c, Basic, a=42, b=.1, test_me=IGNORE)

  def testSubclass(self):
    data = {
      'd': 'bar',
      'e': [
        {
          'a': 1,
          'b': 2.,
          TYPE_FLAG: 'Basic',
        },
        {
          'random': 'stuff',
          'x': True,
        },
      ],
      TYPE_FLAG: 'Subclass',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, Subclass, c=IGNORE, d='bar', e=IGNORE)
    self._check(actual.c, Basic, a=0, b=0., test_me=IGNORE)
    self.assertEqual(list, type(actual.e))
    self.assertEqual(2, len(actual.e))
    self._check(actual.e[0], Basic, a=1, b=2., test_me=IGNORE)
    self.assertEqual({'random': 'stuff', 'x': True}, actual.e[1])

  def testMemberFunction(self):
    # Make sure the member functions are accessible.
    data = {
      TYPE_FLAG: 'Basic',
      'ignored': 'really',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, Basic, a=0, b=0., test_me=IGNORE)
    self.assertEqual(1, actual.test_me())

  def testMultiValue_default(self):
    data = {
      TYPE_FLAG: 'MultiValue',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, MultiValue, f=None, g='')

  def testMultiValue_first(self):
    data  = {
      'f': None,
      'g': 'foo',
      TYPE_FLAG: 'MultiValue',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, MultiValue, f=None, g='foo')

  def testMultiValue_second(self):
    data  = {
      'f': False,
      'g': 3.1,
      TYPE_FLAG: 'MultiValue',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, MultiValue, f=False, g=3.1)

  def testWithInit_default(self):
    data  = {
      TYPE_FLAG: 'WithInit',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, WithInit, h='', i=3)

  def testWithInit_values(self):
    data  = {
      'h': 'foo',
      'i': 4,
      TYPE_FLAG: 'WithInit',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, WithInit, h='foo', i=3)

  def testNotType(self):
    data  = {
      'j': ['a', 2],
      TYPE_FLAG: 'NotType',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, NotType, j=set(['a', 2]), k=23)

  def testTypeOrDict_Basic(self):
    data  = {
      'l': {
        'a': 3,
        'b': 4.0,
        TYPE_FLAG: 'Basic',
      },
      TYPE_FLAG: 'TypeOrDict',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, TypeOrDict, l=IGNORE)
    self._check(actual.l, Basic, a=3, b=4., test_me=IGNORE)

  def testTypeOrDict_dict(self):
    data  = {
      'l': {
        'foo': 'bar',
      },
      TYPE_FLAG: 'TypeOrDict',
    }
    actual = PersistentMixIn.from_dict(marshall(data))
    self._check(actual, TypeOrDict, l={'foo': 'bar'})

  def testStrDisallowed(self):
    data  = {
      TYPE_FLAG: 'StrDisallowed',
    }
    self.assertRaises(TypeError, PersistentMixIn.from_dict, marshall(data))


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.WARNING,
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
