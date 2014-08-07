# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Recipe module to ensure a checkout is consistant on a bot."""


from slave import recipe_api


# This is just for testing, to indicate if a master is using a Git scheduler
# or not.
GIT_MASTERS = ['chromium.git']


def jsonish_to_python(spec, is_top=False):
  """Turn a json spec into a python parsable object.

  This exists because Gclient specs, while resembling json, is actually
  ingested using a python "eval()".  Therefore a bit of plumming is required
  to turn our newly constructed Gclient spec into a gclient-readable spec.
  """
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


class BotUpdateApi(recipe_api.RecipeApi):

  def __call__(self, name, cmd, **kwargs):
    """Wrapper for easy calling of bot_update."""
    assert isinstance(cmd, (list, tuple))
    kwargs.setdefault('abort_on_failure', True)
    bot_update_path = self.m.path['build'].join(
        'scripts', 'slave', 'bot_update.py')
    return self.m.python(name, bot_update_path, cmd, **kwargs)

  def ensure_checkout(self, gclient_config=None, suffix=None,
                      patch=True, update_presentation=True,
                      force=False, **kwargs):
    # We can re-use the gclient spec from the gclient module, since all the
    # data bot_update needs is already configured into the gclient spec.
    cfg = gclient_config or self.m.gclient.c
    spec_string = jsonish_to_python(cfg.as_jsonish(), True)

    # Used by bot_update to determine if we want to run or not.
    master = self.m.properties['mastername']
    builder = self.m.properties['buildername']
    slave = self.m.properties['slavename']

    # Construct our bot_update command.  This basically be inclusive of
    # everything required for bot_update to know:
    root = self.m.properties.get('root')
    if patch:
      issue = self.m.properties.get('issue')
      patchset = self.m.properties.get('patchset')
      patch_url = self.m.properties.get('patch_url')
    else:
      # The trybot recipe sometimes wants to de-apply the patch. In which case
      # we pretend the issue/patchset/patch_url never existed.
      issue = patchset = patch_url = None
    # Issue and patchset must come together.
    if issue:
      assert patchset
    if patchset:
      assert issue
    if patch_url:
      # If patch_url is present, bot_update will actually ignore issue/ps.
      issue = patchset = None

    rev_map = {}
    if self.m.gclient.c:
      rev_map = self.m.gclient.c.got_revision_mapping.as_jsonish()

    flags = [
        # 1. Do we want to run? (master/builder/slave).
        ['--master', master],
        ['--builder', builder],
        ['--slave', slave],

        # 2. What do we want to check out (spec/root/rev/rev_map).
        ['--spec', spec_string],
        ['--root', root],
        ['--revision_mapping_file', self.m.json.input(rev_map)],

        # 3. How to find the patch, if any (issue/patchset/patch_url).
        ['--issue', issue],
        ['--patchset', patchset],
        ['--patch_url', patch_url],

        # 4. Hookups to JSON output back into recipes.
        ['--output_json', self.m.json.output()],]


    revisions = {}
    for solution in cfg.solutions:
      if solution.revision:
        revisions[solution.name] = solution.revision
      elif solution == cfg.solutions[0]:
        revisions[solution.name] = (
            self.m.properties.get('parent_got_revision') or
            self.m.properties.get('revision') or
            'HEAD')
    if self.m.gclient.c and self.m.gclient.c.revisions:
      revisions.update(self.m.gclient.c.revisions)
    for name, revision in sorted(revisions.items()):
      flags.append(['--revision', '%s@%s' % (name, revision)])

    # Filter out flags that are None.
    cmd = [item for flag_set in flags
           for item in flag_set if flag_set[1] is not None]

    if force:
      cmd.append('--force')

    # Inject Json output for testing.
    git_mode = self.m.properties.get('mastername') in GIT_MASTERS
    first_sln = cfg.solutions[0].name
    step_test_data = lambda: self.test_api.output_json(
        master, builder, slave, root, first_sln, rev_map, git_mode, force,
        self.m.properties.get('fail_patch', False))

    def followup_fn(step_result):
      if update_presentation:
        # Set properties such as got_revision.
        if 'properties' in step_result.json.output:
          properties = step_result.json.output['properties']
          for prop_name, prop_value in properties.iteritems():
            step_result.presentation.properties[prop_name] = prop_value
      # Add helpful step description in the step UI.
      if 'step_text' in step_result.json.output:
        step_text = step_result.json.output['step_text']
        step_result.presentation.step_text = step_text
      # Add log line output.
      if 'log_lines' in step_result.json.output:
        for log_name, log_lines in step_result.json.output['log_lines']:
          step_result.presentation.logs[log_name] = log_lines.splitlines()

    # Add suffixes to the step name, if specified.
    name = 'bot_update'
    if not patch:
      name += ' (without patch)'
    if suffix:
      name += ' - %s' % suffix

    # Ah hah! Now that everything is in place, lets run bot_update!
    yield self(name, cmd, followup_fn=followup_fn,
               step_test_data=step_test_data, **kwargs),

    # Set the "checkout" path for the main solution.
    # This is used by the Chromium module to figure out where to look for
    # the checkout.
    bot_update_step = self.m.step_history.last_step()
    # bot_update actually just sets root to be the folder name of the
    # first solution.
    if bot_update_step.json.output['did_run']:
      co_root = bot_update_step.json.output['root']
      cwd = kwargs.get('cwd', self.m.path['slave_build'])
      self.m.path['checkout'] = cwd.join(*co_root.split(self.m.path.sep))
