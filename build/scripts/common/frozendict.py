# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implements a frozen dictionary-like object"""

import collections
import copy

import common.memo as memo

class frozendict(collections.Mapping):
  """A frozen dictionary class"""

  def __init__(self, *args, **kwargs):
    self._data = dict(*args, **kwargs)

  def __iter__(self):
    return iter(self._data)

  def __len__(self):
    return len(self._data)

  def __getitem__(self, key):
    return self._data[key]

  @memo.memo_i()
  def __hash__(self):
    return hash(self.itemtuple())

  def __str__(self):
    return str(self._data)

  def __repr__(self):
    return '%s(%s)' % (type(self).__name__, str(self))

  def __eq__(self, other):
    return (self._data == other)

  def __ne__(self, other):
    return (not self == other)

  def __deepcopy__(self, _memo):
    return copy.deepcopy(self._data)

  @memo.memo_i()
  def itemtuple(self):
    return tuple(sorted(self.iteritems()))

  def mutableDict(self):
    """
    Returns a mutable dictionary copy, replacing 'frozendict' with 'dict's.

    This function uses the 'copy.deepcopy' method to create a mutable deep copy
    of the dictionary.

    Note that due to the one-size-fits-all behavior of 'deepcopy', the result
    can be anything from heavyhanded to incorrect depending on the contents of
    the dictionary. The caller should make sure they understand the operation
    and its behavior on all of the dictionary's subtypes before using it.

    Returns: (dict) A mutable clone of the dictionary and its members.
    """
    return copy.deepcopy(self)

  def extend(self, **kwargs):
    """Returns a copy of this object with the 'kwargs' fields updated."""
    ndata = self.mutableDict()
    ndata.update(kwargs)
    return type(self)(**ndata)
