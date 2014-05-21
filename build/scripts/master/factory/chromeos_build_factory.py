# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Inherits build_factory.BuildFactory to use chromeos_factory."""

from master.factory import build_factory
from master.factory import chromeos_build


class BuildFactory(build_factory.BuildFactory):
  """A Chromium Build Factory that does not compute source stamps."""
  buildClass = chromeos_build.Build
