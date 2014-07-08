# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class IsolateApi(recipe_api.RecipeApi):
  """APIs for interacting with isolates."""

  def __init__(self, **kwargs):
    super(IsolateApi, self).__init__(**kwargs)
    self._isolate_server = 'https://isolateserver.appspot.com'
    self._isolated_tests = {}

  @property
  def isolate_server(self):
    """URL of Isolate server to use, default is a production one."""
    return self._isolate_server

  @isolate_server.setter
  def isolate_server(self, value):
    """Changes URL of Isolate server to use."""
    self._isolate_server = value

  def set_isolate_environment(self, config):
    """Modifies the config to include isolate related GYP_DEFINES.

    Modifies the passed Config (which should generally be api.chromium.c)
    to set up the appropriate GYP_DEFINES to upload isolates to the isolate
    server during the build. This must be called early in your recipe;
    definitely before the checkout and runhooks steps.

    Uses current values of self.isolate_server. It should be property configured
    before calling this method if the default value (production instance of
    Isolate service) is not ok.
    """
    assert config.gyp_env.GYP_DEFINES['component'] != 'shared_library', (
      'isolates don\'t work with the component build yet; see crbug.com/333473')
    config.gyp_env.GYP_DEFINES['test_isolation_mode'] = 'archive'
    config.gyp_env.GYP_DEFINES['test_isolation_outdir'] = self._isolate_server

  def find_isolated_tests(self, build_dir, targets=None):
    """Returns a step which finds all *.isolated files in a build directory.

    Assigns the dict {target name -> *.isolated file hash} to the swarm_hashes
    build property. This implies this step can currently only be run once
    per recipe.

    If |targets| is None, the step will use all *.isolated files it finds.
    Otherwise, it will verify that all |targets| are found and will use only
    them. If some expected targets are missing, will abort the build.
    """
    def followup_fn(step_result):
      assert isinstance(step_result.json.output, dict)
      self._isolated_tests = step_result.json.output
      if targets is not None and step_result.presentation.status != 'FAILURE':
        found = set(step_result.json.output)
        expected = set(targets)
        if found >= expected:
          # Limit result only to |expected|.
          self._isolated_tests = {
            target: step_result.json.output[target] for target in expected
          }
        else:
          # Some expected targets are missing? Fail the step.
          step_result.presentation.status = 'FAILURE'
          step_result.presentation.logs['missing.isolates'] = (
              ['Failed to find *.isolated files:'] + list(expected - found))
      step_result.presentation.properties['swarm_hashes'] = self._isolated_tests
      # No isolated files found? That looks suspicious, emit warning.
      if (not self._isolated_tests and
          step_result.presentation.status != 'FAILURE'):
        step_result.presentation.status = 'WARNING'
    return self.m.python(
        'find isolated tests',
        self.resource('find_isolated_tests.py'),
        [
          '--build-dir', build_dir,
          '--output-json', self.m.json.output(),
        ],
        abort_on_failure=True,
        followup_fn=followup_fn,
        step_test_data=lambda: (self.test_api.output_json(targets)))

  @property
  def isolated_tests(self):
    """The dictionary of 'target name -> isolated hash' for this run.

    These come either from the incoming swarm_hashes build property,
    or from calling find_isolated_tests, above, at some point during the run.
    """
    hashes = self.m.properties.get('swarm_hashes', self._isolated_tests)
    return {
      k.encode('ascii'): v.encode('ascii') 
      for k, v in hashes.iteritems()
    }

  @property
  def _run_isolated_path(self):
    """Returns the path to run_isolated.py."""
    return self.m.swarming_client.path.join('run_isolated.py')

  def runtest_args_list(self, test, args=None):
    """Array of arguments for running the given test via run_isolated.py.

    The test should be already uploaded to the isolated server. The method
    expects to find |test| as a key in the isolated_tests dictionary.
    """
    assert test in self.isolated_tests, (test, self.isolated_tests)
    full_args = [
      '-H',
      self.isolated_tests[test],
      '-I',
      self._isolate_server,
    ]
    if args:
      full_args.append('--')
      full_args.extend(args)
    return full_args

  def runtest(self, test, revision, webkit_revision, args=None, name=None,
              master_class_name=None, **runtest_kwargs):
    """Runs a test which has previously been isolated to the server.

    Uses runtest_args_list, above, and delegates to api.chromium.runtest.
    """
    return self.m.chromium.runtest(
        self._run_isolated_path,
        args=self.runtest_args_list(test, args),
        # We must use the name of the test as the name in order to avoid
        # duplicate steps called "run_isolated".
        name=name or test,
        revision=revision,
        webkit_revision=webkit_revision,
        master_class_name=master_class_name,
        **runtest_kwargs)

  def run_telemetry_test(self, isolate_name, test,
                         revision, webkit_revision,
                         args=None, name=None, master_class_name=None,
                         **runtest_kwargs):
    """Runs a Telemetry test which has previously isolated to the server.

    Uses runtest_args_list, above, and delegates to
    api.chromium.run_telemetry_test.
    """
    return self.m.chromium.run_telemetry_test(
        self._run_isolated_path,
        test,
        # When running the Telemetry test via an isolate we need to tell
        # run_isolated.py the hash and isolate server first, and then give
        # the isolate the test name and other arguments separately.
        prefix_args=self.runtest_args_list(isolate_name) + ['--'],
        args=args,
        name=name,
        revision=revision,
        webkit_revision=webkit_revision,
        master_class_name=master_class_name,
        **runtest_kwargs)
