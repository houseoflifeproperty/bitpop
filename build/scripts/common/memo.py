# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Collection of decorators to help optimize Python functions and classes
by caching return values.

Return values are (by default) keyed off of the function's parameters.
Consequently, any parameters that are used in memoization must be hashable.

This library offers two styles of memoization:
1) Absolute memoization (memo) uses the full set of parameters against a
   per-function memo dictionary. If this is used on an instance method, the
   'self' parameter is included in the key.
2) Instance memoization (memo_i) uses a per-instance memoization dictionary.
   The dictionary is stored as a member ('_memo__dict') of of the instance.
   Consequently, the 'self' parameter is no longer needed/used in the
   memoization key, removing the need to have the instance itself support being
   hashed.

Memoized function state can be cleared by calling the memoized function's
'memo_clear' method.
"""

import inspect


class MemoizedFunction(object):
  """Handles the memoization state of a given memoized function."""

  # Memoization constant to represent 'un-memoized' (b/c 'None' is a valid
  # result)
  class _EMPTY(object):
    pass
  EMPTY = _EMPTY()

  def __init__(self, func, ignore):
    """
    Args:
      func: (function) The function to memoize
      ignore: (container) The names of 'func' parameters to ignore when
          generating its memo key. Only parameters that have no effect on the
          output of the function should be included.
    """
    self.func = func
    self.ignore = ignore
    self.im_self = None
    self.im_class = None

  def __repr__(self):
    properties = [str(self.func)]
    if self.im_self is not None:
      properties.append('bound=%s' % (self.im_self,))
    if len(self.ignore) > 0:
      properties.append('ignore=%s' % (','.join(self.ignore)))
    return '%s(%s)' % (type(self).__name__, ', '.join(properties))

  def __get__(self, obj, klass=None):
    # Make this callable class a bindable Descriptor
    if klass is None:
      klass = type(obj)
    self.im_self = obj
    self.im_class = klass
    return self

  def _get_memo_dict(self):
    """Returns: (dict) the memoization dictionary to store return values in."""
    raise NotImplementedError()

  def _get_call_args(self, args):
    """Returns the call arguments, factoring in 'self' if this method is bound.
    """
    if self.im_self is not None:
      return (self.im_self,) + args
    return args

  def _key(self, args, kwargs):
    """Returns: the memoization key for a set of function arguments.

    This 'ignored' parameters are removed prior to generating the key.
    """
    call_params = inspect.getcallargs(self.func, *args, **kwargs)
    return tuple((k, v)
                 for k, v in sorted(call_params.iteritems())
                 if k not in self.ignore)

  def _call_memo(self, memo_key, args, kwargs):
    """Retrieves the memoized function result.

    If the memoized function has not been memoized, it will be invoked;
    otherwise, the memoized value will be returned.

    Args:
      memo_key: The generated memoization key for this invocation.
      args, kwargs: Function parameters (only used if not memoized yet)
    Returns:
      The memoized function's return value.
    """
    memo_dict = self._get_memo_dict()
    result = memo_dict.get(memo_key, self.EMPTY)
    if result is self.EMPTY:
      result = memo_dict[memo_key] = self.func(*args, **kwargs)
    return result

  def memo_clear(self, *args, **kwargs):
    """Clears memoization results for a given set of arguments.
    If no memoized result is stored for the supplied parameters, this function
    is a no-op.

    Args:
      args, kwargs: Memoization function parameters whose memoized value should
          be cleared.
    """
    memo_key = self._key(args, kwargs)
    self._get_memo_dict().pop(memo_key, None)


class StaticMemoizedFunction(MemoizedFunction):
  """A MemoizedFunction bound to a static dictionary"""
  def __init__(self, *args, **kwargs):
    super(StaticMemoizedFunction, self).__init__(*args, **kwargs)
    self.memo_dict = {}

  def _get_memo_dict(self):
    return self.memo_dict

  def __call__(self, *args, **kwargs):
    # Prepend 'self' to 'args' if bound
    args = self._get_call_args(args)

    # Key off full unbound/bound args
    return self._call_memo(
        self._key(args, kwargs),
        args,
        kwargs,
    )


class InstanceMemoizedFunction(MemoizedFunction):
  """A MemoizedFunction bound to an instance function's instance dictionary"""

  def __init__(self, attr_name, *args, **kwargs):
    super(InstanceMemoizedFunction, self).__init__(*args, **kwargs)
    self.attr_name = attr_name

  def _get_memo_dict(self):
    # Get/create the instance-specific memo dictionary
    memo_dict = getattr(self.im_self, self.attr_name, None)
    if memo_dict is None:
      memo_dict = {}
      setattr(self.im_self, self.attr_name, memo_dict)
    return memo_dict

  def _key(self, args, kwargs):
    # Stub out 'self' with 'None' since we are implicitly keying off of 'self'
    # via its instance dictionary.
    return super(InstanceMemoizedFunction, self)._key(
        (None,) + args,
        kwargs,
    )

  def __call__(self, *args, **kwargs):
    # Key off bound args/kwargs (doesn't include 'self'). When we invoke the
    return self._call_memo(
        self._key(args, kwargs),
        self._get_call_args(args), # Prepend 'self' to 'args'
        kwargs,
    )


def memo(ignore=()):
  """Generic function memoization decorator.

  This memoizes a specific function using a function key.

  The following example memoizes the function absolutely. It will be executed
  once and, after that, will only returned cached results.

  @memo.memo(ignore=('print_debug_output',))
  def my_method(print_debug_output=False):
    # Perform complex calculation
    if print_debug_output:
      print 'The calculated result is: %r' % (result)
    return result

  The following example memoizes for unique values of 'param1' and 'param2',
  but not 'print_debug_output' since it doesn't affect the function's result:

  @memo.memo()
  def my_method(param1, param2):
    # Perform complex calculation using 'param1' and 'param2'
    if print_debug_output:
      print 'The calculated result for (%r, %r) is: %r' %
            (param1, param2, result)
    return result

  Args:
    ignore: (list) The names of parameters to ignore when memoizing.
    memo_dict:
        - If None, a function-global memoization dictionary will be used
  """
  def wrap(func):
    return StaticMemoizedFunction(
        func,
        ignore=ignore,
    )
  return wrap

def memo_i(ignore=(), attr_name=None):
  """Memoization decorator which uses an instance-local dictionary.

  Instance methods can use this decorator to store memoization state in a
  local instance dictionary rather than the default class-wide dictionary. This
  offers several advantages:
  - The instance's memoization will be collect when it is collected
  - Memoization will avoid the instance's __eq__ and __hash__ functions
    (allowing them to be memoized).

  class MyClass(object):
    @memo.memo_i()
    def func(self):
      # Perform complicated calculation
      return result

  Args:
    ignore: (list) The names of parameters to ignore when memoizing.
    attr_name: (None/str) The name of the instance-local attribute to use as the
        memoization dictionary; if 'None', a default variable name will be
        used.
  """
  def wrap(func):
    return InstanceMemoizedFunction(
        attr_name or '_memo__dict',
        func,
        ignore=ignore,
    )
  return wrap
