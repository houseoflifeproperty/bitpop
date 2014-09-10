# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class BaseAndroidApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(BaseAndroidApi, self).__init__(**kwargs)
    self._env = {}

  def envsetup(self):
    """Use envsetup.sh to read environment variables to use for Android.

    This environment will be used for runhooks, compile and test_runner with the
    exception for the GYP_* variables, which are excluded to avoid confusion
    with settings in the chromium recipe module config.
    """
    envsetup_cmd = [self.m.path['checkout'].join('build', 'android',
                                                 'envsetup.sh')]

    cmd = ([self.m.path['build'].join('scripts', 'slave', 'env_dump.py'),
            '--output-json', self.m.json.output()] + envsetup_cmd)
    result = self.m.step('envsetup', cmd, env=self._env)

    env_diff = result.json.output
    self._env.update((k, v) for k, v in env_diff.iteritems()
                     if not k.startswith('GYP_'))

  def runhooks(self):
    self.m.chromium.runhooks(env=self._env)

  def compile(self):
    self.m.chromium.compile(env=self._env)

  def test_runner(self, test):
    script = self.m.path['checkout'].join('build', 'android', 'test_runner.py')
    args = ['gtest', '-s', test, '--verbose']
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      args += ['--release']
    self.m.python(test, script, args, env=self._env)
