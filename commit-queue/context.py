# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class Context(object):
  """Class to hold context about a the current code review and checkout."""
  def __init__(self, rietveld, checkout, status):
    self.rietveld = rietveld
    self.checkout = checkout
    self.status = status
