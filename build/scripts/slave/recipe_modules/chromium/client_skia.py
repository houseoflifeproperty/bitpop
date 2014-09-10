# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_linux
from . import chromium_mac
from . import chromium_win
import copy

# The Skia config just clones some regular Chromium builders, except that they
# use an up-to-date Skia.

# This list specifies which Chromium builders to "copy".
_builders = [
#  SPEC Module     Test Spec File         Builder Names
  (chromium_linux, 'chromium.linux.json', ['Linux Builder', 'Linux Tests']),
  (chromium_win,   'chromium.win.json',   ['Win Builder', 'Win7 Tests (1)']),
  (chromium_mac,   'chromium.mac.json',   ['Mac Builder', 'Mac10.7 Tests (1)']),
]

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-skia-gm',
  },
  'builders': {},
}

for spec_module, test_spec_file, builders_list in _builders:
  for builder_name in builders_list:
    builder_cfg = copy.deepcopy(spec_module.SPEC['builders'][builder_name])
    builder_cfg['recipe_config'] = 'chromium_skia'
    builder_cfg['testing']['test_spec_file'] = test_spec_file
    SPEC['builders'][builder_name] = builder_cfg
