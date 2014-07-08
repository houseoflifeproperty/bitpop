# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


class V8Api(recipe_api.RecipeApi):
  def checkout(self, **kwargs):
    return self.m.gclient.checkout(**kwargs)

  def runhooks(self, **kwargs):
    return self.m.chromium.runhooks(**kwargs)

  def update_clang(self):
    # TODO(machenbach): Implement this for windows or unify with chromium's
    # update clang step as soon as it exists.
    return self.m.step(
        'update clang',
        [self.m.path['checkout'].join('tools', 'clang',
                                      'scripts', 'update.sh')],
        env={'LLVM_URL': ChromiumSvnSubURL(self.m.gclient.c, 'llvm-project')})

  def compile(self, **kwargs):
    return self.m.chromium.compile(**kwargs)

  def presubmit(self):
    return self.m.python(
      'Presubmit',
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      ['--testname', 'presubmit'],
      cwd=self.m.path['checkout'],
    )

  def check_initializers(self):
    return self.m.step(
      'Static-Initializers',
      ['bash',
       self.m.path['checkout'].join('tools', 'check-static-initializers.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def gc_mole(self):
    # TODO(machenbach): Make gcmole work with absolute paths. Currently, a
    # particular clang version is installed on one slave in '/b'.
    env = {
      'CLANG_BIN': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole', 'bin')
      ),
      'CLANG_PLUGINS': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole')
      ),
    }
    return self.m.step(
      'GCMole',
      ['lua', self.m.path.join('tools', 'gcmole', 'gcmole.lua')],
      cwd=self.m.path['checkout'],
      env=env,
    )

  def simple_leak_check(self):
    # TODO(machenbach): Add task kill step for windows.
    relative_d8_path = self.m.path.join(
        self.m.path.basename(self.m.chromium.c.build_dir),
        self.m.chromium.c.build_config_fs,
        'd8')
    return self.m.step(
      'Simple Leak Check',
      ['valgrind', '--leak-check=full', '--show-reachable=yes',
       '--num-callers=20', relative_d8_path, '-e', '"print(1+2)"'],
      cwd=self.m.path['checkout'],
    )

  def _runtest(self, name, test, flaky_tests=None, **kwargs):
    env = {}
    full_args = [
      '--target', self.m.chromium.c.build_config_fs,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['target_arch'],
      '--testname', test['tests'],
    ]

    # Add test-specific test arguments.
    full_args += test.get('test_args', [])

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    if self.c.testing.SHARD_COUNT > 1:
      full_args += [
        '--shard_count=%d' % self.c.testing.SHARD_COUNT,
        '--shard_run=%d' % self.c.testing.SHARD_RUN,
      ]

    if flaky_tests:
      full_args += ['--flaky-tests', flaky_tests]

    # Arguments and environment for asan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') == 1:
      full_args.append('--asan')
      env['ASAN_SYMBOLIZER_PATH'] = self.m.path['checkout'].join(
          'third_party', 'llvm-build', 'Release+Asserts', 'bin',
          'llvm-symbolizer')

    return self.m.python(
      name,
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      full_args,
      cwd=self.m.path['checkout'],
      env=env,
      **kwargs
    )

  def runtest(self, test, **kwargs):
    # Get the flaky-step configuration default per test.
    add_flaky_step = test.get('add_flaky_step', False)

    # Overwrite the flaky-step configuration on a per builder basis as some
    # types of builders (e.g. branch, try) don't have any flaky steps.
    if self.c.testing.add_flaky_step is not None:
      add_flaky_step = self.c.testing.add_flaky_step
    if add_flaky_step:
      return [
        self._runtest(test['name'], test, flaky_tests='skip', **kwargs),
        self._runtest(test['name'] + ' - flaky', test, flaky_tests='run',
                      abort_on_failure=False, **kwargs),
      ]
    else:
      return self._runtest(test['name'], test, **kwargs)
