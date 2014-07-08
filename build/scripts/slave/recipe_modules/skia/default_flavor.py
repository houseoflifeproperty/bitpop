# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import base_flavor


"""Default flavor utils class, used for desktop builders."""


class DefaultFlavorUtils(base_flavor.BaseFlavorUtils):

  def step(self, name, cmd, **kwargs):
    """Wrapper for the Step API; runs a step as appropriate for this flavor."""
    path_to_app = self._skia_api.m.chromium.output_dir.join(cmd[0])
    if (self._skia_api.m.platform.is_linux and
        'x86_64' in self._skia_api.builder_name and
        not 'TSAN' in self._skia_api.builder_name):
      new_cmd = ['catchsegv', path_to_app]
    else:
      new_cmd = [path_to_app]
    new_cmd.extend(cmd[1:])
    return self._skia_api.m.step(name, new_cmd, **kwargs)
