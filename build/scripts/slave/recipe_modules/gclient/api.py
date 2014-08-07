# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

def jsonish_to_python(spec, is_top=False):
  ret = ''
  if is_top:  # We're the 'top' level, so treat this dict as a suite.
    ret = '\n'.join(
      '%s = %s' % (k, jsonish_to_python(spec[k])) for k in sorted(spec)
    )
  else:
    if isinstance(spec, dict):
      ret += '{'
      ret += ', '.join(
        "%s: %s" % (repr(str(k)), jsonish_to_python(spec[k]))
        for k in sorted(spec)
      )
      ret += '}'
    elif isinstance(spec, list):
      ret += '['
      ret += ', '.join(jsonish_to_python(x) for x in spec)
      ret += ']'
    elif isinstance(spec, basestring):
      ret = repr(str(spec))
    else:
      ret = repr(spec)
  return ret

class GclientApi(recipe_api.RecipeApi):
  # Singleton object to indicate to checkout() that we should run a revert if
  # we detect that we're on the tryserver.
  RevertOnTryserver = object()

  def __init__(self, **kwargs):
    super(GclientApi, self).__init__(**kwargs)
    self.USE_MIRROR = None
    self._spec_alias = None

  def __call__(self, name, cmd, **kwargs):
    """Wrapper for easy calling of gclient steps."""
    assert isinstance(cmd, (list, tuple))
    prefix = 'gclient '
    if self.spec_alias:
      prefix = ('[spec: %s] ' % self.spec_alias) + prefix

    return self.m.python(prefix + name,
                         self.m.path['depot_tools'].join('gclient.py'),
                         cmd,
                         **kwargs)

  @property
  def use_mirror(self):
    """Indicates if gclient will use mirrors in its configuration."""
    if self.USE_MIRROR is None:
      self.USE_MIRROR = self.m.properties.get('use_mirror', True)
    return self.USE_MIRROR

  @use_mirror.setter
  def use_mirror(self, val):  # pragma: no cover
    self.USE_MIRROR = val

  @property
  def spec_alias(self):
    """Optional name for the current spec for step naming."""
    return self._spec_alias

  @spec_alias.setter
  def spec_alias(self, name):
    self._spec_alias = name

  @spec_alias.deleter
  def spec_alias(self):
    self._spec_alias = None

  def get_config_defaults(self):
    ret = {
      'USE_MIRROR': self.use_mirror
    }
    ret['CACHE_DIR'] = self.m.path['root'].join('git_cache')
    return ret

  def sync(self, cfg, **kwargs):
    kwargs.setdefault('abort_on_failure', True)

    revisions = []
    for i, s in enumerate(cfg.solutions):
      if s.safesync_url:  # prefer safesync_url in gclient mode
        continue
      if i == 0 and s.revision is None:
        s.revision = self.m.properties.get('orig_revision',
                                           self.m.properties.get('revision'))

      if s.revision is not None and s.revision != '':
        revisions.extend(['--revision', '%s@%s' % (s.name, s.revision)])

    for name, revision in sorted(cfg.revisions.items()):
      revisions.extend(['--revision', '%s@%s' % (name, revision)])

    def parse_got_revision(step_result):
      data = step_result.json.output
      for path, info in data['solutions'].iteritems():
        # gclient json paths always end with a slash
        path = path.rstrip('/')
        if path in cfg.got_revision_mapping:
          propname = cfg.got_revision_mapping[path]
          step_result.presentation.properties[propname] = info['revision']

    test_data_paths = set(cfg.got_revision_mapping.keys() +
                          [s.name for s in cfg.solutions])
    step_test_data = lambda: (
      self.test_api.output_json(test_data_paths, cfg.GIT_MODE))
    if not cfg.GIT_MODE:
      yield self('sync', ['sync', '--nohooks', '--delete_unversioned_trees',
                 '--force', '--verbose'] +
                 revisions + ['--output-json', self.m.json.output()],
                 followup_fn=parse_got_revision, step_test_data=step_test_data,
                 **kwargs)
    else:
      # clean() isn't used because the gclient sync flags passed in checkout()
      # do much the same thing, and they're more correct than doing a separate
      # 'gclient revert' because it makes sure the other args are correct when
      # a repo was deleted and needs to be re-cloned (notably
      # --with_branch_heads), whereas 'revert' uses default args for clone
      # operations.
      #
      # TODO(mmoss): To be like current official builders, this step could just
      # delete the whole <slave_name>/build/ directory and start each build
      # from scratch. That might be the least bad solution, at least until we
      # have a reliable gclient method to produce a pristine working dir for
      # git-based builds (e.g. maybe some combination of 'git reset/clean -fx'
      # and removing the 'out' directory).
      j = '-j2' if self.m.platform.is_win else '-j8'
      yield self('sync',
                 ['sync', '--verbose', '--with_branch_heads', '--nohooks', j,
                  '--reset', '--delete_unversioned_trees', '--force',
                  '--upstream', '--no-nag-max'] + revisions +
                 ['--output-json', self.m.json.output()],
                 followup_fn=parse_got_revision, step_test_data=step_test_data,
                 **kwargs)

  def inject_parent_got_revision(self, gclient_config=None, override=False):
    """Match gclient config to build revisions obtained from build_properties.

    Args:
      gclient_config (gclient config object) - The config to manipulate. A value
        of None manipulates the module's built-in config (self.c).
      override (bool) - If True, will forcibly set revision and custom_vars
        even if the config already contains values for them.
    """
    cfg = gclient_config or self.c

    for prop, custom_var in cfg.parent_got_revision_mapping.iteritems():
      val = str(self.m.properties.get(prop, ''))
      if val:
        # Special case for 'src', inject into solutions[0]
        if custom_var is None:
          if cfg.solutions[0].revision is None or override:
            cfg.solutions[0].revision = val
        else:
          if custom_var not in cfg.solutions[0].custom_vars or override:
            cfg.solutions[0].custom_vars[custom_var] = val

  def checkout(self, gclient_config=None, revert=RevertOnTryserver,
               inject_parent_got_revision=True, **kwargs):
    """Return a step generator function for gclient checkouts."""
    cfg = gclient_config or self.c
    assert cfg.complete()

    if revert is self.RevertOnTryserver:
      revert = self.m.tryserver.is_tryserver

    if inject_parent_got_revision:
      self.inject_parent_got_revision(cfg, override=True)

    spec_string = jsonish_to_python(cfg.as_jsonish(), True)

    yield self('setup', ['config', '--spec', spec_string], **kwargs)

    if not cfg.GIT_MODE:
      if revert:
        yield self.revert(**kwargs)
      yield self.sync(cfg, **kwargs)
    else:
      yield self.sync(cfg, **kwargs)

      cfg_cmds = [
        ('user.name', 'local_bot'),
        ('user.email', 'local_bot@example.com'),
      ]
      for var, val in cfg_cmds:
        name = 'recurse (git config %s)' % var
        yield self(name, ['recurse', 'git', 'config', var, val], **kwargs)

    cwd = kwargs.get('cwd', self.m.path['slave_build'])
    if 'checkout' not in self.m.path:
      self.m.path['checkout'] = cwd.join(
        *cfg.solutions[0].name.split(self.m.path.sep))

  def revert(self, **kwargs):
    """Return a gclient_safe_revert step."""
    # Not directly calling gclient, so don't use self().
    alias = self.spec_alias
    prefix = '%sgclient ' % (('[spec: %s] ' % alias) if alias else '')

    kwargs.setdefault('abort_on_failure', True)

    return self.m.python(prefix + 'revert',
        self.m.path['build'].join('scripts', 'slave', 'gclient_safe_revert.py'),
        ['.', self.m.path['depot_tools'].join('gclient',
                                              platform_ext={'win': '.bat'})],
        **kwargs
    )

  def runhooks(self, args=None, **kwargs):
    """Return a 'gclient runhooks' step."""
    args = args or []
    assert isinstance(args, (list, tuple))
    return self('runhooks', ['runhooks'] + list(args), **kwargs)

  @property
  def is_blink_mode(self):
    """ Indicates wether the caller is to use the Blink config rather than the
    Chromium config. This may happen for one of two reasons:
    1. The builder is configured to always use TOT Blink. (factory property
       top_of_tree_blink=True)
    2. A try job comes in that applies to the Blink tree. (root is
       src/third_party/WebKit)
    """
    if self.m.properties.get('top_of_tree_blink'):
      return True

    # Normalize slashes to take into account possible Windows paths.
    root = self.m.properties.get('root', '').replace('\\', '/').lower()

    if root.endswith('third_party/webkit'):
      return True

    return False

  def break_locks(self):
    """Remove all index.lock files. If a previous run of git crashed, bot was
    reset, etc... we might end up with leftover index.lock files.
    """
    yield self.m.python.inline(
      'cleanup index.lock',
      """
        import os, sys

        build_path = sys.argv[1]
        if os.path.exists(build_path):
          for (path, dir, files) in os.walk(build_path):
            for cur_file in files:
              if cur_file.endswith('index.lock'):
                path_to_file = os.path.join(path, cur_file)
                print 'deleting %s' % path_to_file
                os.remove(path_to_file)
      """,
      args = [self.m.path['slave_build']]
    )
