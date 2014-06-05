# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from slave import recipe_api
from slave import recipe_config_types


class SkiaApi(recipe_api.RecipeApi):

  def setup(self):
    self.builder_name = self.m.properties['buildername']
    self.set_config('skia', BUILDER_NAME=self.builder_name)
    self.c.flavor.set_skia_api(self)

  def checkout_steps(self):
    """Run the steps to obtain a checkout of Skia."""
    yield self.m.gclient.checkout()
    yield self.m.tryserver.maybe_apply_issue()

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia.

    Args:
        clobber: bool; whether or not to "clean" before building.
    """
    # Optionally clean before building.
    if clobber or self.m.tryserver.is_tryserver:
      yield self.m.step('clean',
                        ['make', 'clean'],
                        cwd=self.m.path['checkout'])

    # Run GYP to generate project files.
    env = dict(self.c.gyp_env.as_jsonish())
    yield self.m.python(name='gyp_skia', script='gyp_skia', env=env,
                        cwd=self.m.path['checkout'], abort_on_failure=True)

    # Compile each target.
    for target in ['most']:
      yield self.m.step('build %s' % target, ['make', target],
                        cwd=self.m.path['checkout'], abort_on_failure=True)

  def test_steps(self):
    """Run all Skia test executables."""
    # Unit tests.
    yield self.c.flavor.step('tests', ['tests'])

    # GM
    yield self.c.flavor.step('gm', ['gm'])

