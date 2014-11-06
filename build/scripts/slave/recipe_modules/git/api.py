# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api

class GitApi(recipe_api.RecipeApi):
  _GIT_HASH_RE = re.compile('[0-9a-f]{40}', re.IGNORECASE)

  def __call__(self, *args, **kwargs):
    """Return a git command step."""
    run = kwargs.pop('run', True)
    name = kwargs.pop('name', 'git '+args[0])
    if 'cwd' not in kwargs:
      kwargs.setdefault('cwd', self.m.path['checkout'])
    git_cmd = 'git'
    if self.m.platform.is_win:
      git_cmd = self.m.path['depot_tools'].join('git.bat')
    can_fail_build = kwargs.pop('can_fail_build', True)
    try:
      return self.m.step(name, [git_cmd] + list(args), infra_step=True,
                         **kwargs)
    except self.m.step.StepFailure as f:
      if can_fail_build:
        raise
      else:
        return f.result

  def fetch_tags(self, **kwargs):
    """Fetches all tags from the origin."""
    kwargs.setdefault('name', 'git fetch tags')
    self('fetch', 'origin', '--tags', **kwargs)

  def checkout(self, url, ref=None, dir_path=None, recursive=False,
               submodules=True, keep_paths=None, step_suffix=None,
               curl_trace_file=None, can_fail_build=True):
    """Returns an iterable of steps to perform a full git checkout.
    Args:
      url (string): url of remote repo to use as upstream
      ref (string): ref to fetch and check out
      dir_path (Path): optional directory to clone into
      recursive (bool): whether to recursively fetch submodules or not
      submodules (bool): whether to sync and update submodules or not
      keep_paths (iterable of strings): paths to ignore during git-clean;
          paths are gitignore-style patterns relative to checkout_path.
      step_suffix (string): suffix to add to a each step name
      curl_trace_file (Path): if not None, dump GIT_CURL_VERBOSE=1 trace to that
          file. Useful for debugging git issue reproducible only on bots. It has
          a side effect of all stderr output of 'git fetch' going to that file.
      can_fail_build (bool): if False, ignore errors during fetch or checkout.
    """
    if not dir_path:
      dir_path = url.rsplit('/', 1)[-1]
      if dir_path.endswith('.git'):  # ex: https://host/foobar.git
        dir_path = dir_path[:-len('.git')]

      # ex: ssh://host:repo/foobar/.git
      dir_path = dir_path or dir_path.rsplit('/', 1)[-1]

      dir_path = self.m.path['slave_build'].join(dir_path)

    if 'checkout' not in self.m.path:
      self.m.path['checkout'] = dir_path

    git_setup_args = ['--path', dir_path, '--url', url]
    if self.m.platform.is_win:
      git_setup_args += ['--git_cmd_path',
                         self.m.path['depot_tools'].join('git.bat')]

    step_suffix = '' if step_suffix is  None else ' (%s)' % step_suffix
    steps = [
        self.m.python(
            'git setup%s' % step_suffix,
            self.m.path['build'].join('scripts', 'slave', 'git_setup.py'),
            git_setup_args),
    ]

    # There are five kinds of refs we can be handed:
    # 0) None. In this case, we default to properties['branch'].
    # 1) A 40-character SHA1 hash.
    # 2) A fully-qualifed arbitrary ref, e.g. 'refs/foo/bar/baz'.
    # 3) A fully qualified branch name, e.g. 'refs/heads/master'.
    #    Chop off 'refs/heads' and now it matches case (4).
    # 4) A branch name, e.g. 'master'.
    # Note that 'FETCH_HEAD' can be many things (and therefore not a valid
    # checkout target) if many refs are fetched, but we only explicitly fetch
    # one ref here, so this is safe.
    fetch_args = []
    if not ref:                                  # Case 0
      fetch_remote = 'origin'
      fetch_ref = self.m.properties.get('branch') or 'master'
      checkout_ref = 'FETCH_HEAD'
    elif self._GIT_HASH_RE.match(ref):        # Case 1.
      fetch_remote = 'origin'
      fetch_ref = ''
      checkout_ref = ref
    elif ref.startswith('refs/heads/'):       # Case 3.
      fetch_remote = 'origin'
      fetch_ref = ref[len('refs/heads/'):]
      checkout_ref = 'FETCH_HEAD'
    else:                                     # Cases 2 and 4.
      fetch_remote = 'origin'
      fetch_ref = ref
      checkout_ref = 'FETCH_HEAD'

    fetch_args = [x for x in (fetch_remote, fetch_ref) if x]
    if recursive:
      fetch_args.append('--recurse-submodules')

    fetch_env = {}
    fetch_stderr = None
    if curl_trace_file:
      fetch_env['GIT_CURL_VERBOSE'] = '1'
      fetch_stderr = self.m.raw_io.output(leak_to=curl_trace_file)

    self('fetch', *fetch_args,
      cwd=dir_path,
      name='git fetch%s' % step_suffix,
      env=fetch_env,
      stderr=fetch_stderr,
      can_fail_build=can_fail_build)
    self('checkout', '-f', checkout_ref,
      cwd=dir_path,
      name='git checkout%s' % step_suffix,
      can_fail_build=can_fail_build)

    clean_args = list(self.m.itertools.chain(
        *[('-e', path) for path in keep_paths or []]))

    self('clean', '-f', '-d', '-x', *clean_args,
      name='git clean%s' % step_suffix,
      cwd=dir_path,
      can_fail_build=can_fail_build)

    if submodules:
      self('submodule', 'sync',
        name='submodule sync%s' % step_suffix,
        cwd=dir_path,
        can_fail_build=can_fail_build)
      self('submodule', 'update', '--init', '--recursive',
        name='submodule update%s' % step_suffix,
        cwd=dir_path,
        can_fail_build=can_fail_build)

  def get_timestamp(self, commit='HEAD', test_data=None, **kwargs):
    """Find and return the timestamp of the given commit."""
    step_test_data = None
    if test_data is not None:
      step_test_data = lambda: self.m.raw_io.test_api.stream_output(test_data)
    return self('show', commit, '--format=%at', '-s',
                stdout=self.m.raw_io.output(),
                step_test_data=step_test_data).stdout.rstrip()

