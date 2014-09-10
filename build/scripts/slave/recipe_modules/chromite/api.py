# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ChromiteApi(recipe_api.RecipeApi):
  manifest_url = 'https://chromium.googlesource.com/chromiumos/manifest.git'
  repo_url = 'https://chromium.googlesource.com/external/repo.git'
  chromite_subpath = 'chromite'

  def checkout(self, manifest_url=None, repo_url=None):
    manifest_url = manifest_url or self.manifest_url
    repo_url = repo_url or self.repo_url

    self.m.repo.init(manifest_url, '--repo-url', repo_url)
    self.m.repo.sync()

  def cbuildbot(self, name, config, flags=None, chromite_path=None, **kwargs):
    """Return a step to run a command inside the cros_sdk."""
    chromite_path = (chromite_path or
                     self.m.path['slave_build'].join(self.chromite_subpath))
    arg_list = []
    for k, v in sorted((flags or {}).items()):
      if v is not None:
        arg_list.append('--%s=%s' % (k, v))
      else:
        arg_list.append('--%s' % k)

    arg_list.append(config)

    cmd = self.m.path.join(chromite_path, 'bin', 'cbuildbot')

    # TODO(petermayo): Wrap this nested annotation in a stabilizing wrapper.
    self.m.python(name, cmd, arg_list, allow_subannotations=True,
                  **kwargs)


  def cros_sdk(self, name, cmd, flags=None, environ=None, chromite_path=None,
                 **kwargs):
    """Return a step to run a command inside the cros_sdk."""
    chromite_path = (chromite_path or
                     self.m.path['slave_build'].join(self.chromite_subpath))

    chroot_cmd = self.m.path.join(chromite_path, 'bin', 'cros_sdk')

    arg_list = []
    for k, v in sorted((flags or {}).items()):
      arg_list.extend(['--%s' % k, v])
    for t in sorted((environ or {}).items()):
      arg_list.append('%s=%s' % t)
    arg_list.append('--')
    arg_list.extend(cmd)

    self.m.python(name, chroot_cmd, arg_list, **kwargs)

  def setup_board(self, board, flags=None, **kwargs):
    """Run the setup_board script inside the chroot."""
    self.cros_sdk('setup board',
                  ['./setup_board', '--board', board],
                  flags, **kwargs)

  def build_packages(self, board, flags=None, **kwargs):
    """Run the build_packages script inside the chroot."""
    self.cros_sdk('build packages',
                  ['./build_packages', '--board', board],
                  flags, **kwargs)
