# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Base class for all flavor utils classes."""


class BaseFlavorUtils(object):

  def __init__(self):
    """Create a flavor utils instance.

    Since these classes need access to the APIs used by SkiaApi, we need an
    instance of SkiaApi.
    """
    self._skia_api = None

  def set_skia_api(self, skia_api):
    """Attach this flavor utils instance to a SkiaApi instance.

    This method must be called before any others.
    """
    self._skia_api = skia_api

  def step(self, name, cmd, **kwargs):
    """Wrapper for the Step API; runs a step as appropriate for this flavor."""
    raise NotImplementedError

  def __repr__(self):
    return '<%s object>' % self.__class__.__name__
