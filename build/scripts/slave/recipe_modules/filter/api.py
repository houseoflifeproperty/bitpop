# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api

class FilterApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(FilterApi, self).__init__(**kwargs)
    self._result = False
    self._matching_exes = []
    self._compile_targets = []
    self._paths = []

  def __is_path_in_exclusion_list(self, path, exclusions):
    """Returns true if |path| matches any of the regular expressions in
    |exclusions|."""
    for regex in exclusions:
      match = regex.match(path)
      if match and match.end() == len(path):
        return regex.pattern
    return False

  @property
  def result(self):
    """Returns the result from most recent call to
    does_patch_require_compile."""
    return self._result

  @property
  def matching_exes(self):
    """Returns the set of exes passed to does_patch_require_compile() that
    are effected by the set of files that have changed."""
    return self._matching_exes

  @property
  def compile_targets(self):
    """Returns the set of targets that need to be compiled based on the set of
    files that have changed."""
    return self._compile_targets

  @property
  def paths(self):
    """Returns the paths that have changed in this patch."""
    return self._paths

  def _load_analyze_config(self, file_name):
    config_path = self.m.path.join('testing', 'buildbot', file_name)
    step_result = self.m.json.read(
      'read filter exclusion spec',
      self.m.path['checkout'].join(config_path),
      step_test_data=lambda: self.m.json.test_api.output({
          'base': {
            'exclusions': [],
          },
          'chromium': {
            'exclusions': [],
          },
        })
      )
    step_result.presentation.step_text = 'path: %r' % config_path
    return step_result.json.output

  def _load_exclusions(self, names, file_name):
    file_contents = self._load_analyze_config(file_name)
    exclusions = []
    for name in names:
      exclusions.extend(file_contents[name]['exclusions'])
    return exclusions

  def does_patch_require_compile(self, exes=None, compile_targets=None,
                                 additional_name=None,
                                 config_file_name='trybot_analyze_config.json',
                                 **kwargs):
    """Return true if the current patch requires a build (and exes to run).
    Return value can be accessed by call to result().

    Args:
      exes: the possible set of executables that are desired to run. When done
      matching_exes() returns the set of exes that are effected by the files
      that have changed.
      compile_targets: proposed set of targets to compile.
      additional_name: an additional top level key to look up exclusoions in,
      see |config_file_name|.
      conconfig_file_name: the config file to look up exclusions in.
      Within the file we concatenate "base.exclusions" and
      "|additional_name|.exclusions" (if |additional_name| is not none) to get
      the full list of exclusions.
      the exclusions should be list of python regular expressions (as strings).
      If any of the files in the current patch match one of the values in
      |exclusions| True is returned (by way of result()).
      """
    names = ['base']
    if additional_name is not None:
      names.append(additional_name)
    exclusions = self._load_exclusions(names, config_file_name)

    self._matching_exes = exes if exes is not None else []
    self._compile_targets = compile_targets if compile_targets is not None \
                                            else []

    # Get the set of files in the current patch.
    step_result = self.m.git('diff', '--cached', '--name-only',
                             name='git diff to analyze patch',
                             stdout=self.m.raw_io.output(),
                             step_test_data=lambda:
                               self.m.raw_io.test_api.stream_output('foo.cc'))
    self._paths = step_result.stdout.split()

    # Check the path of each file against the exclusion list. If found, no need
    # to check dependencies.
    exclusion_regexs = [re.compile(exclusion) for exclusion in exclusions]
    for path in self.paths:
      first_match = self.__is_path_in_exclusion_list(path, exclusion_regexs)
      if first_match:
        step_result.presentation.logs.setdefault('excluded_files', []).append(
            '%s (regex = \'%s\')' % (path, first_match))
        self._result = True
        return

    analyze_input = {'files': self.paths, 'targets': self._matching_exes}

    test_output = {'status': 'No dependency',
                   'targets': [],
                   'build_targets': []}

    kwargs.setdefault('env', {})
    kwargs['env'].update(self.m.chromium.c.gyp_env.as_jsonish())

    try:
      step_result = self.m.python('analyze',
                          self.m.path['checkout'].join('build', 'gyp_chromium'),
                          args=['--analyzer',
                                self.m.json.input(analyze_input),
                                self.m.json.output()],
                          step_test_data=lambda: self.m.json.test_api.output(
                            test_output),
                          **kwargs)
    except self.m.step.StepFailure as f:
      # Continue on if there is an error executing python. Most likely runhooks
      # will fail too, but errors there are more well understood than here.
      self._result = True
      step_result = f.result
      step_result.presentation.status = 'WARNING'
      return

    if 'error' in step_result.json.output:
      self._result = True
      step_result.presentation.step_text = 'Error: ' + \
          step_result.json.output['error']
    elif step_result.json.output['status'] == 'Found dependency':
      self._result = True
      self._matching_exes = step_result.json.output['targets']
      self._compile_targets = step_result.json.output['build_targets']
    elif step_result.json.output['status'] == 'Found dependency (all)':
      self._result = True
    else:
      step_result.presentation.step_text = 'No compile necessary'
