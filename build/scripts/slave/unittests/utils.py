#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A collection of utils used by slave unittests."""

import test_env  # pylint: disable=W0403,W0611

import contextlib
import coverage

@contextlib.contextmanager
def print_coverage(include=None):
  cov = coverage.coverage(include=include)
  cov.start()
  try:
    yield
  finally:
    cov.stop()
    cov.report()
