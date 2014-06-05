# Copyright (c) 2014 ThE Chromium Authors. All Rights Reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class AdbApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AdbApi, self).__init__(**kwargs)
    self._devices = None

  def _adb_path(self):
    return str(self.m.path['build_internal'].join('scripts', 'slave',
                                                  'android', 'adb'))

  def list_devices(self):
    cmd = [
        self._adb_path(),
        'devices',
    ]

    yield self.m.python(
        'List adb devices',
        self.resource('list_devices.py'),
        args=[ repr(cmd), self.m.json.output() ],
        step_test_data=self.test_api.device_list)

    step = self.m.step_history.last_step()
    self._devices = step.json.output

  @property
  def devices(self):
    assert self._devices is not None, (
        "devices is only available after yielding list_devices()")
    return self._devices

  def root_devices(self):
    yield self.list_devices()
    yield self.m.python.inline(
        'Root devices',
        """
        import subprocess
        import sys
        adb_path = sys.argv[1]
        for device in sys.argv[2:]:
          subprocess.check_call([adb_path, '-s', device, 'root'])
          subprocess.check_call([adb_path, '-s', device, 'wait-for-device'])
        """,
        args=[self._adb_path()] + self.devices)
