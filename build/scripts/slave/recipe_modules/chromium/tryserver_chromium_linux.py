# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from . import chromium_linux
from . import steps


SPEC = {
  'settings': chromium_linux.SPEC['settings'],
  'builders': {
    # This is intended to build in the same was as the main linux builder.
    'bisect_builder': chromium_linux.SPEC['builders']['Linux Builder'],
  },
}
