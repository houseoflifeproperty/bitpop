# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defines the PersistentMixIn utility class to easily convert classes to and
from dict for serialization.

This class is aimed at json-compatible serialization, so it supports the limited
set of structures supported by json; strings, numbers as int or float, list and
dictionaries.

PersistentMixIn._persistent_members() returns a dict of each member with the
tuple of expected types. Each member can be decoded in multiple types, for
example, a subversion revision number could have (None, int, str), meaning that
the revision could be None, when not known, an int or the int as a string
representation. The tuple is listed in the prefered order of conversions.

Composites types that cannot be represented exactly in json like tuple, set and
frozenset are converted from and back to list automatically. Any class instance
that has been serialized can be unserialized in the same class instance or into
a bare dict.

See tests/model_tests.py for examples.
"""

import json
import logging
import os

# Set in the output dict to be able to know which class was serialized to help
# deserialization.
TYPE_FLAG = '__persistent_type__'

# Marker to tell the deserializer that we don't know the expected type, used in
# composite types.
_UNKNOWN = object()


def as_dict(value):
  """Recursively converts an object into a dictionary.

  Converts tuple,set,frozenset into list and recursively process each items.
  """
  if hasattr(value, 'as_dict') and callable(value.as_dict):
    return value.as_dict()
  elif isinstance(value, (list, tuple, set, frozenset)):
    return [as_dict(v) for v in value]
  elif isinstance(value, dict):
    return dict((as_dict(k), as_dict(v))
                for k, v in value.iteritems())
  elif isinstance(value, (bool, float, int, basestring)) or value is None:
    return value
  else:
    raise AttributeError('Can\'t type %s into a dictionary' % type(value))


def _inner_from_dict(name, value, member_types):
  """Recursively regenerates an object.

  For each of the allowable types, try to convert it. If None is an allowable
  type, any data that can't be parsed will be parsed as None and will be
  silently discarded. Otherwise, an exception will be raise.
  """
  logging.debug('_inner_from_dict(%s, %r, %s)', name, value, member_types)
  result = None
  if member_types is _UNKNOWN:
    # Use guesswork a bit more and accept anything.
    if isinstance(value, dict):
      if TYPE_FLAG in value:
        result = PersistentMixIn.from_dict(value, _UNKNOWN)
      else:
        # Unserialize it as a raw dict.
        result =  dict(
            (_inner_from_dict(None, k, _UNKNOWN),
              _inner_from_dict(None, v, _UNKNOWN))
            for k, v in value.iteritems())
    elif isinstance(value, list):
      # All of these are serialized to list.
      result = [_inner_from_dict(None, v, _UNKNOWN) for v in value]
    elif isinstance(value, (bool, float, int, unicode)):
      result = value
    else:
      raise TypeError('No idea how to convert %r' % value)
  else:
    for member_type in member_types:
      # Explicitly leave None out of this loop.
      if issubclass(member_type, PersistentMixIn):
        if isinstance(value, dict) and TYPE_FLAG in value:
          result = PersistentMixIn.from_dict(value, member_type)
          break
      elif member_type is dict:
        if isinstance(value, dict):
          result =  dict(
              (_inner_from_dict(None, k, _UNKNOWN),
                _inner_from_dict(None, v, _UNKNOWN))
              for k, v in value.iteritems())
          break
      elif member_type in (list, tuple, set, frozenset):
        # All of these are serialized to list.
        if isinstance(value, list):
          result = member_type(
              _inner_from_dict(None, v, _UNKNOWN) for v in value)
          break
      elif member_type in (bool, float, int, str, unicode):
        if isinstance(value, member_type):
          result = member_type(value)
          break
      elif member_type is None.__class__ and value is None:
        result = None
        break
    else:
      logging.info(
          'Ignored %s: %r; didn\'t fit types %s',
          name, value,
          ', '.join(i.__name__ for i in member_types))
    _check_type_value(name, result, member_types)
  return result


def to_yaml(obj):
  """Converts a PersistentMixIn into a yaml-inspired format.

  Warning: Not unit tested, use at your own risk!
  """
  def align(x):
    y = x.splitlines(True)
    if len(y) > 1:
      return ''.join(y[0:1] + ['  ' + z for z in y[1:]])
    return x
  def align_value(x):
    if '\n' in x:
      return '\n  ' + align(x)
    return x

  if hasattr(obj, 'as_dict') and callable(obj.as_dict):
    out = (to_yaml(obj.as_dict()),)
  elif isinstance(obj, (bool, float, int, unicode)) or obj is None:
    out = (align(str(obj)),)
  elif isinstance(obj, dict):
    if TYPE_FLAG in obj:
      out = ['%s:' % obj[TYPE_FLAG]]
    else:
      out = []
    for k, v in obj.iteritems():
      # Skips many members resolving to bool() == False
      if k.startswith('__') or v in (None, '', False, 0):
        continue
      r = align_value(to_yaml(v))
      if not r:
        continue
      out.append('- %s: %s' % (k, r))
  elif hasattr(obj, '__iter__') and callable(obj.__iter__):
    out = ['- %s' % align(to_yaml(x)) for x in obj]
  else:
    out = ('%s' % obj.__class__.__name__,)
  return '\n'.join(out)


def _default_value(member_types):
  """Returns an instance of the first allowed type. Special case None."""
  if member_types[0] is None.__class__:
    return None
  else:
    return member_types[0]()


def _check_type_value(name, value, member_types):
  """Raises a TypeError exception if value is not one of the allowed types in
  member_types.
  """
  if not isinstance(value, member_types):
    prefix = '%s e' % name if name else 'E'
    raise TypeError(
        '%sxpected type(s) %s; got %r' %
        (prefix, ', '.join(i.__name__ for i in member_types), value))



class PersistentMixIn(object):
  """Class to be used as a base class to persistent data in a simplistic way.

  Persistent class member needs to be set to a tuple containing the instance
  member variable that needs to be saved or loaded. The first item will be
  default value, e.g.:
    foo = (None, str, dict)
  Will default initialize self.foo to None.
  """
  # Cache of all the subclasses of PersistentMixIn.
  __persistent_classes_cache = None

  def __init__(self, **kwargs):
    """Initializes with the default members."""
    super(PersistentMixIn, self).__init__()
    persistent_members = self._persistent_members()
    for member, member_types in persistent_members.iteritems():
      if member in kwargs:
        value = kwargs.pop(member)
        if isinstance(value, str):
          # Assume UTF-8 all the time. Note: This is explicitly when the object
          # is constructed in the code. This code path is never used when
          # deserializing the object.
          value = value.decode('utf-8')
      else:
        value = _default_value(member_types)
      _check_type_value(member, value, member_types)
      setattr(self, member, value)
    if kwargs:
      raise AttributeError('Received unexpected initializers: %s' % kwargs)

  @classmethod
  def _persistent_members(cls):
    """Returns the persistent items as a dict.

    Each entry value can be a tuple when the member can be assigned different
    types.
    """
    # Note that here, cls is the subclass, not PersistentMixIn.
    # TODO(maruel): Cache the results. It's tricky because setting
    # cls.__persistent_members_cache on a class will implicitly set it on its
    # subclass. So in a class hierarchy with A -> B -> PersistentMixIn, calling
    # B()._persistent_members() will incorrectly set the cache for A.
    persistent_members_cache = {}
    # Enumerate on the subclass, not on an instance.
    for item in dir(cls):
      if item.startswith('_'):
        continue
      item_value = getattr(cls, item)
      if isinstance(item_value, type):
        item_value = (item_value,)
      if not isinstance(item_value, tuple):
        continue
      if not all(i is None or i.__class__ == type for i in item_value):
        continue
      if any(i is str for i in item_value):
        raise TypeError(
            '%s is type \'str\' which is currently not supported' % item)
      item_value = tuple(
          f if f is not None else None.__class__ for f in item_value)
      persistent_members_cache[item] = item_value
    return persistent_members_cache

  @staticmethod
  def _get_subclass(typename):
    """Returns the PersistentMixIn subclass with the name |typename|."""
    subclass = None
    if PersistentMixIn.__persistent_classes_cache is not None:
      subclass = PersistentMixIn.__persistent_classes_cache.get(typename)
    if not subclass:
      # Get the subclasses recursively.
      PersistentMixIn.__persistent_classes_cache = {}
      def recurse(c):
        for s in c.__subclasses__():
          assert s.__name__ not in PersistentMixIn.__persistent_classes_cache
          PersistentMixIn.__persistent_classes_cache[s.__name__] = s
          recurse(s)
      recurse(PersistentMixIn)

      subclass = PersistentMixIn.__persistent_classes_cache.get(typename)
      if not subclass:
        raise KeyError('Couldn\'t find type %s' % typename)
    return subclass

  def as_dict(self):
    """Create a dictionary out of this object, i.e. Serialize the object."""
    out = {}
    for member, member_types in self._persistent_members().iteritems():
      value = getattr(self, member)
      _check_type_value(member, value, member_types)
      out[member] = as_dict(value)
    out[TYPE_FLAG] = self.__class__.__name__
    return out

  @staticmethod
  def from_dict(data, subclass=_UNKNOWN):
    """Returns an instance of a class inheriting from PersistentMixIn,
    initialized with 'data' dict, i.e. Deserialize the object.
    """
    logging.debug('from_dict(%r, %s)', data, subclass)
    if subclass is _UNKNOWN:
      subclass = PersistentMixIn._get_subclass(data[TYPE_FLAG])
    # This initializes the instance with the default values.
    try:
      obj = subclass()
    except TypeError:
      # pylint: disable=E1103
      logging.error('Failed to instantiate %s', subclass.__name__)
      raise
    assert isinstance(obj, PersistentMixIn) and obj.__class__ != PersistentMixIn
    # pylint: disable=W0212
    for member, member_types in obj._persistent_members().iteritems():
      if member in data:
        try:
          value = _inner_from_dict(member, data[member], member_types)
        except TypeError:
          # pylint: disable=E1103
          logging.error('Failed to instantiate %s', subclass.__name__)
          raise
      else:
        value = _default_value(member_types)
      _check_type_value(member, value, member_types)
      setattr(obj, member, value)
    return obj

  def __str__(self):
    return to_yaml(self)


def load_from_json_file(filename):
  """Loads one object from a JSON file."""
  try:
    f = open(filename, 'r')
    return PersistentMixIn.from_dict(json.load(f))
  finally:
    f.close()


def save_to_json_file(filename, obj):
  """Save one object in a JSON file."""
  try:
    old = filename + '.old'
    if os.path.exists(filename):
      os.rename(filename, old)
  finally:
    try:
      f = open(filename, 'w')
      json.dump(obj.as_dict(), f, sort_keys=True, indent=2)
      f.write('\n')
    finally:
      f.close()
