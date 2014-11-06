# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Module to allow a Twisted 'defer.inlineCallbacks'-style generator to
be used both asynchronously (through Twisted) and synchronously.

This module works by having code implement logic through framework-independent
'yield'-based coroutines similar to how Twisted uses 'inlineCallbacks'.
Hybrid methods are then invoked against a 'HybridBase' implementation, at which
point they pick up implementation-specific details and behaviors.

@hybrid.inlineCallbacks
def readStrippedData(read_data_func):
  data = yield read_data_func()
  hybrid.returnValue(data.strip())

Functions decorated with 'hybrid.inlineCallbacks' can then be invoked in one of
the following ways:

1) Directly through a hybrid implementation's `call' method
2) Yielded in a hybrid coroutine.
3) Called directly as a member function of a class that uses a Hybrid MixIn.

Current implementations include:
- 'Twisted': Hybrid coroutines return and can yield Deferred objects in a
    manner identical to 'defer.inlineCallbacks'.
- 'Synchronous': Coroutines are executed synchronously and return their
    evaluated results.

For example, when executing the 'readStrippedData' hybrid coroutine through
the Twisted framework, one would define a Deferred-based data source and
execute the function through the Twisted `call' method:

# Example using `hybrid.Twisted' hybrid base.
def twistedReadFile(agent):
  d = hybrid.Twisted.call(readStrippedData)(
      agent.read,
  )
  def processData(data):
    print('Read data:', data)
  d.addCallback(processData)
  return d
# END `hybrid.Twisted' example

The same function can be called synchronously by supplying a
synchronous-compatible `read_data_func' parameter and invoking through the
`hybrid.Synchronous.call' method:

# Example using `hybrid.Synchronous' hybrid base.
def synchronousReadFile(fd):
  data = hybrid.Synchronous.call(readStrippedData)(
      fd.read,
  )
  print('Read data:', data)
  return data
# END `hybrid.Synchronous' example

Abstract base classes can define abstract hybrid logic with the expectation
that subclasses specialize them to a specific hybrid base. For example:

class BaseReader(object):
  def _read(self, fd):
    raise NotImplementedError()

  @hybrid.inlineCallbacks
  def complexReadLogic(self, fd):
    while True:
      data = yield self._read(fd)
      # (...)
      if condition:
        hybrid.returnValue(result)

class TwistedReader(BaseReader, hybrid.Twisted.MixIn):
  # Overrides 'BaseReader._read'
  def _read(self, fd):
    d = defer.Deferred()
    twisted.internet.fdesc.readFromFD(fd, d.callback)
    return d

class SynchronousReader(BaseReader, hybrid.Synchronous.MixIn):
  # Overrides 'BaseReader._read'
  def _read(self, fd):
    return fd.read()

This allows complex multipart logic to be defined in a central
backend-independent class and attached to an implementation independently.

Behind the scenes, the `hybrid' module runs `inlineCallbacks' methods through
a lightweight inner reactor that proxies between generalized hybrid functions
and the hybrid base's implementation.

For the Twisted implementation, this reactor falls through directly to
Twisted's implementation of 'inlineCallbacks' and 'returnValue'.

For the Synchronous implementation, the reactor passes through to an outer
reactor that executes the respective methods synchronously.
"""

import types

import common.memo as memo
from functools import wraps

__all__ = (
    'Synchronous',
    'Twisted',
    'inlineCallbacks',
    'returnValue',
    )

HYBRID_CONTEXT_KWARG = '__hybrid_context'

class _HybridReturnValue(Exception):
  def __init__(self, value):
    super(_HybridReturnValue, self).__init__()
    self.value = value


class HybridBase(object):
  # Disable 'no __init__ method' warning | pylint: disable=W0232

  class MixIn:
    @staticmethod
    def _hybrid__getHybridContext():
      raise NotImplementedError()

  @classmethod
  def getHybridContext(cls):
    raise NotImplementedError()

  @classmethod
  def call(cls, inline_callback):
    """
    Returns: (func) a proxy function for 'inline_callback' that invokes it with
        a hybrid base.
    """
    @wraps(inline_callback)
    def wrapper(*args, **kwargs):
      kwargs[HYBRID_CONTEXT_KWARG] = cls.getHybridContext()
      return inline_callback(*args, **kwargs)
    return wrapper


class Synchronous(HybridBase):
  # Disable 'no __init__ method' warning | pylint: disable=W0232
  """Hybrid base that executes coroutines synchronously"""

  class MixIn(HybridBase.MixIn):
    # Disable 'no __init__ method' warning | pylint: disable=W0232
    """Synchronous MixIn uses the synchronous hybrid context"""
    @staticmethod
    def _hybrid__getHybridContext():
      return Synchronous.getHybridContext()

  @classmethod
  @memo.memo()
  def getHybridContext(cls):
    # Serially execute the 'inlineCallbacks' methods
    def synchronousInlineCallbacks(func):
      @wraps(func)
      def wrap(*args, **kwargs):
        result = None
        gen = func(*args, **kwargs)
        try:
          while True:
            result = gen.send(result)
        except _HybridReturnValue, e:
          return e.value
        except StopIteration:
          return None
      return wrap

    def synchronousReturnValue(value):
      raise _HybridReturnValue(value)

    return (synchronousInlineCallbacks, synchronousReturnValue)


class Twisted(HybridBase):
  """Hybrid base that returns Twisted Deferreds."""

  class MixIn(HybridBase.MixIn):
    # Disable 'no __init__ method' warning | pylint: disable=W0232

    @staticmethod
    def _hybrid__getHybridContext():
      return Twisted.getHybridContext()

  @classmethod
  @memo.memo()
  def getHybridContext(cls):
    from twisted.internet import defer
    return (defer.inlineCallbacks, defer.returnValue)


class InlineCallbackInvocation(object):
  def __init__(self, func, *args, **kwargs):
    self.func = func
    self.args = args
    self.kwargs = kwargs

    # Get the argument-passed context, if one is defined
    self.context = kwargs.pop(HYBRID_CONTEXT_KWARG, None)

  def __repr__(self):
    return '%s%s' % (type(self).__name__, self.func)

  def _runWithContext(self, context, *args, **kwargs):
    if context is None:
      raise ValueError("Failed to get hybrid context for %r(*%r, **%r)" % (
                       self.func, args, kwargs))

    result = None
    g = self.func(*args, **kwargs)
    if not isinstance(g, types.GeneratorType):
      raise TypeError("Hybrid function %r is not a generator" % (self.func,))

    while g:
      try:
        result = g.send(result)

        # Unwrap and forward context to nested 'inlineCallbacks'
        if isinstance(result, type(self)):
          result = result(context)
        result = yield result
      except _HybridReturnValue, e:
        result = e.value
        g = None
      except StopIteration:
        result = None
        g = None
    context[1](result)

  def __call__(self, context=None):
    # Run our hybrid generator through the outer 'inlineCallbacks'
    return context[0](self._runWithContext)(
        (context or self.context),
        *self.args,
        **self.kwargs)

#
# Standard public interface
#

def inlineCallbacks(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    invocation = InlineCallbackInvocation(func, *args, **kwargs)

    context = kwargs.pop(HYBRID_CONTEXT_KWARG, None)
    if context is None:
      if len(args) > 0:
        func_self = args[0]
        # Fetch the context from the MixIn, if args[0] is 'self'
        if isinstance(func_self, HybridBase.MixIn):
          # 'Access to protected member' warning | pylint: disable=W0212
          context = func_self._hybrid__getHybridContext()

    # Behave differently based on how we're being used. If a context is
    # available to us, assume that we are being bootstrapped (either by a
    # 'HybridBase.call' variant directly via MixIn magic). In this case,
    # evaluate against that context and return the actual result.
    if context:
      return invocation(context)

    # Otherwise, assume we are being used in the middle of a hybrid reactor.
    # In this case, we want the reactor to supply the context that it's using
    # to us directly. Therefore, we will return the 'InlineCallbackInvocation'
    # object and let the reactor call it.
    return invocation
  return wrapper

def returnValue(val):
  raise _HybridReturnValue(val)
