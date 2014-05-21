# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Defines errors and stack trace utility funciton."""

import breakpad
import sys
import traceback


class ConfigurationError(Exception):
  """Configuration issues that prevents startup."""


def send_stack(e):
  breakpad.SendStack(e,
      ''.join(traceback.format_tb(sys.exc_info()[2])),
      maxlen=2000)
