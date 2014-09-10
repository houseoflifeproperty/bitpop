# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from . import chromium_chromiumos

SPEC = copy.deepcopy(chromium_chromiumos.SPEC)

SPEC['settings']['build_gs_bucket'] = 'chromium-webkit-archive'
for b in SPEC['builders'].itervalues():
    b['gclient_apply_config'] = ['blink']
