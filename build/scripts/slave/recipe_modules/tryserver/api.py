# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from slave import recipe_api


PATCH_STORAGE_RIETVELD = 'rietveld'
PATCH_STORAGE_GIT = 'git'
PATCH_STORAGE_SVN = 'svn'


class TryserverApi(recipe_api.RecipeApi):
  @property
  def patch_url(self):
    """Reads patch_url property and corrects it if needed."""
    url = self.m.properties.get('patch_url')
    return url

  @property
  def is_tryserver(self):
    """Returns true iff we can apply_issue or patch."""
    return self.can_apply_issue or self.is_patch_in_svn or self.is_patch_in_git

  @property
  def can_apply_issue(self):
    """Returns true iff the properties exist to apply_issue from rietveld."""
    return (self.m.properties.get('rietveld')
            and 'issue' in self.m.properties
            and 'patchset' in self.m.properties)

  @property
  def is_patch_in_svn(self):
    """Returns true iff the properties exist to patch from a patch URL."""
    return self.patch_url

  @property
  def is_patch_in_git(self):
    return (self.m.properties.get('patch_storage') == PATCH_STORAGE_GIT and
            self.m.properties.get('patch_repo_url') and
            self.m.properties.get('patch_ref'))

  def _apply_patch_step(self, patch_file=None, patch_content=None, root=None):
    assert not (patch_file and patch_content), (
        'Please only specify either patch_file or patch_content, not both!')
    patch_cmd = [
        'patch',
        '--dir', root or self.m.path['checkout'],
        '--force',
        '--forward',
        '--remove-empty-files',
        '--strip', '0',
    ]
    if patch_file:
      patch_cmd.extend(['--input', patch_file])

    yield self.m.step('apply patch', patch_cmd,
                      stdin=patch_content,
                      abort_on_failure=True)

  def apply_from_svn(self, cwd):
    """Downloads patch from patch_url using svn-export and applies it"""
    # TODO(nodir): accept these properties as parameters
    patch_url = self.patch_url
    root = self.m.properties.get('root') or cwd

    def link_patch(step_result):
      """Links the patch.diff file on the waterfall."""
      step_result.presentation.logs['patch.diff'] = (
          step_result.raw_io.output.split('\n'))

    patch_file = self.m.raw_io.output('.diff')
    ext = '.bat' if self.m.platform.is_win else ''
    svn_cmd = ['svn' + ext, 'export', '--force', patch_url, patch_file]

    yield self.m.step('download patch', svn_cmd, followup_fn=link_patch,
                      step_test_data=self.test_api.patch_content,
                      abort_on_failure=True)

    if self.m.platform.is_win:
      patch_content = self.m.raw_io.input(
        self.m.step_history.last_step().raw_io.output)
      yield self.m.python.inline(
          'convert line endings (win32)',
          r"""
            import sys
            out = open(sys.argv[1], "w")
            for line in sys.stdin:
              out.write(line)
          """,
          args=[self.m.raw_io.output()],
          stdin=patch_content,
          followup_fn=link_patch,
          step_test_data=self.test_api.patch_content_windows,
          abort_on_failure=True,
      )

    patch_content = self.m.raw_io.input(
        self.m.step_history.last_step().raw_io.output)
    yield self._apply_patch_step(patch_content=patch_content, root=root)

  def apply_from_git(self, cwd):
    """Downloads patch from given git repo and ref and applies it"""
    # TODO(nodir): accept these properties as parameters
    patch_repo_url = self.m.properties['patch_repo_url']
    patch_ref = self.m.properties['patch_ref']

    patch_dir = self.m.path.mkdtemp('patch')
    git_setup_py = self.m.path['build'].join('scripts', 'slave', 'git_setup.py')
    git_setup_args = ['--path', patch_dir, '--url', patch_repo_url]
    patch_path = patch_dir.join('patch.diff')

    yield (
        self.m.python('patch git setup', git_setup_py, git_setup_args,
                      abort_on_failure=True),
        self.m.git('fetch', 'origin', patch_ref,
                   name='patch fetch', cwd=patch_dir, abort_on_failure=True),
        self.m.git('clean', '-f', '-d', '-x',
                   name='patch clean', cwd=patch_dir, abort_on_failure=True),
        self.m.git('checkout', '-f', 'FETCH_HEAD',
                   name='patch git checkout', cwd=patch_dir,
                   abort_on_failure=True),
        self._apply_patch_step(patch_file=patch_path, root=cwd),
        self.m.step('remove patch', ['rm', '-rf', patch_dir]),
    )

  def determine_patch_storage(self):
    """Determines patch_storage automatically based on properties."""
    storage = self.m.properties.get('patch_storage')
    if storage:
      return storage

    if self.can_apply_issue:
      return PATCH_STORAGE_RIETVELD
    elif self.is_patch_in_svn:
      return PATCH_STORAGE_SVN

  def maybe_apply_issue(self, cwd=None, authentication=None):
    """If we're a trybot, apply a codereview issue.

    Args:
      cwd: If specified, apply the patch from the specified directory.
      authentication: authentication scheme whenever apply_issue.py is called.
        This is only used if the patch comes from Rietveld. Possible values:
        None, 'oauth2' (see also api.rietveld.apply_issue.)
    """
    storage = self.determine_patch_storage()

    if storage == PATCH_STORAGE_RIETVELD:
      yield self.m.rietveld.apply_issue(
          self.m.rietveld.calculate_issue_root(),
          authentication=authentication)
    elif storage == PATCH_STORAGE_SVN:
      yield self.apply_from_svn(cwd)
    elif storage == PATCH_STORAGE_GIT:
      yield self.apply_from_git(cwd)
    else:
      # Since this method is "maybe", we don't raise an Exception.
      pass
