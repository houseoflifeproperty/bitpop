# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

import os

from buildbot.steps import shell
from buildbot.process.properties import Property, WithProperties

from common import chromium_utils
from master import chromium_step
from master.factory import build_factory
from master.factory import chromeos_build_factory
from master.factory import commands
from master.log_parser import process_log

import config


class ChromiteFactory(object):
  """
  Create a build factory that runs a chromite script.

  This is designed mainly to utilize build scripts directly hosted in
  chromite.git.

  Attributes:
      script: the name of the chromite command to run (bin/<foo>)
      params: string of parameters to pass to the main command.
      b_params:  An array of StepParameters to pass to the main command.
      timeout: Timeout in seconds for the main command. Default 9000 seconds.
      branch: git branch of the chromite repo to pull.
      crostools_repo: git repo for crostools toolset.
      chromite_repo: git repo for chromite toolset.
      factory: a factory with pre-existing steps to extend rather than start
          fresh.  Allows composing.
      use_chromeos_factory: indicates we want a default of a chromeos factory.
      slave_manager: whether we should manage the script area for the bot.
      chromite_patch: a url and ref pair (dict) to patch the checked out
          chromite. Fits well with a single change from a codereview, to use
          on one or more builders for realistic testing, or experiments.
      sleep_sync: Whether to randomly delay the start of the chromite step.
      show_gclient_output: Set to False to hide the output of 'gclient sync'.
          Used by external masters to prevent leaking sensitive information,
          since both external and internal slaves use internal.DEPS/.
  """
  _default_git_base = 'http://git.chromium.org/chromiumos'
  _default_crostools = None
  _default_chromite = _default_git_base + '/chromite.git'

  def __init__(self, script, params=None, b_params=None, timeout=9000,
               branch='master', crostools_repo=_default_crostools,
               chromite_repo=_default_chromite,
               factory=None, use_chromeos_factory=False, slave_manager=True,
               chromite_patch=None, sleep_sync=None,
               show_gclient_output=True):
    if chromite_patch:
      assert ('url' in chromite_patch and 'ref' in chromite_patch)

    self.branch = branch
    self.chromite_patch = chromite_patch
    self.chromite_repo = chromite_repo
    self.timeout = timeout
    self.show_gclient_output = show_gclient_output
    self.slave_manager = slave_manager
    self.sleep_sync = sleep_sync

    if factory:
      self.f_cbuild = factory
    elif use_chromeos_factory:
      # Suppresses revisions, at the moment.
      self.f_cbuild = chromeos_build_factory.BuildFactory()
    else:
      self.f_cbuild = build_factory.BuildFactory()

    self.add_bootstrap_steps()
    if script:
      self.add_chromite_step(script, params, b_params)

  def _git_clear_and_checkout(self, repo, patch=None):
    """rm -rf and clone the basename of the repo passed without .git

    Args:
      repo: ssh: uri for the repo to be checked out
      patch: object with url and ref to patch on top
    """
    git_bin = '/usr/bin/git'
    git_checkout_dir = os.path.basename(repo).replace('.git', '')
    clear_and_clone_cmd = 'rm -rf %s' % git_checkout_dir
    clear_and_clone_cmd += ' && %s clone %s' % (git_bin, repo)
    clear_and_clone_cmd += ' && cd %s' % git_checkout_dir

    # We ignore branches coming from buildbot triggers and rely on those in the
    # config.  This is because buildbot branch names do not match up with
    # cros builds.
    clear_and_clone_cmd += ' && %s checkout %s' % (git_bin, self.branch)
    msg = 'Clear and Clone %s' % git_checkout_dir
    if patch:
      clear_and_clone_cmd += (' && %s pull %s %s' %
                              (git_bin, patch['url'], patch['ref']))
      msg = 'Clear, Clone and Patch %s' % git_checkout_dir

    self.f_cbuild.addStep(shell.ShellCommand,
                          command=clear_and_clone_cmd,
                          name=msg,
                          description=msg,
                          haltOnFailure=True)

  def add_bootstrap_steps(self):
    """Bootstraps Chromium OS Build by syncing pre-requisite repositories.

    * gclient sync of /b
    * clearing of chromite
    * clean checkout of chromite
    """
    if self.slave_manager:
      build_slave_sync = ['gclient', 'sync',
                          '--delete_unversioned_trees']
      self.f_cbuild.addStep(shell.ShellCommand,
                            command=build_slave_sync,
                            name='update_scripts',
                            description='Sync buildbot slave files',
                            workdir='/b',
                            timeout=300,
                            want_stdout=self.show_gclient_output,
                            want_stderr=self.show_gclient_output)

    if self.sleep_sync:
      # We run a script from the script checkout above.
      fuzz_start = ['python', 'scripts/slave/random_delay.py',
                    '--max=%g' % self.sleep_sync]
      self.f_cbuild.addStep(shell.ShellCommand,
                            command=fuzz_start,
                            name='random_delay',
                            description='Delay start of build',
                            workdir='/b/build',
                            timeout=int(self.sleep_sync) + 10)

    self._git_clear_and_checkout(self.chromite_repo, self.chromite_patch)

  def add_chromite_step(self, script, params, b_params):
    """Adds a step that runs a chromite command.

    Args:
      script:  Name of the script to run from chromite/bin.
      params:  A string containing extra parameters for the script.
      b_params:  An array of StepParameters.
    """
    cmd = ['chromite/bin/%s' % script]
    if b_params:
      cmd.extend(b_params)
    if params:
      cmd.extend(params.split())

    self.f_cbuild.addStep(chromium_step.AnnotatedCommand,
                          command=cmd,
                          timeout=self.timeout,
                          name=script,
                          description=script,
                          usePTY=False)

  def get_factory(self):
    """Returns the produced factory."""
    return self.f_cbuild


class CbuildbotFactory(ChromiteFactory):
  """
  Create a build factory that runs the cbuildbot script.

  Attributes:
      params: string of parameters to pass to the cbuildbot command.
      script: name of the cbuildbot command.  Default cbuildbot.
      buildroot: buildroot to set. Default /b/cbuild.
      dry_run: Means cbuildbot --debug, or don't push anything (cbuildbot only)
      trybot: Whether this is creating builders for the trybot waterfall.
      chrome_root: The place to put or use the chrome source.
      pass_revision: to pass the chrome revision desired into the build.
      perf_file: If set, name of the perf file to upload.
      perf_base_url: If set, base url to build into references.
      perf_output_dir: If set, where the perf files are to update.
      *: anything else is passed to the base Chromite class.
  """

  def __init__(self,
               params,
               script='cbuildbot',
               buildroot='/b/cbuild',
               dry_run=False,
               trybot=False,
               chrome_root=None,
               pass_revision=None,
               perf_file=None,
               perf_base_url=None,
               perf_output_dir=None,
               **kwargs):
    super(CbuildbotFactory, self).__init__(None, None,
        use_chromeos_factory=not pass_revision, **kwargs)

    self.buildroot = buildroot
    self.dry_run = dry_run
    self.script = script
    self.trybot = trybot
    self.chrome_root = chrome_root
    self.pass_revision = pass_revision

    if params:
      self.add_cbuildbot_step(params)

    if perf_file:
      self.add_perf_step(params, perf_file, perf_base_url, perf_output_dir)


  def add_cbuildbot_step(self, params):
    self.add_chromite_step(self.script, params, self.compute_buildbot_params())


  def compute_buildbot_params(self):
    cmd = [WithProperties('--buildnumber=%(buildnumber)s'),
           '--buildroot=%s' % self.buildroot]

    if self.trybot:
      cmd.append(Property('extra_args'))
    else:
      cmd += ['--buildbot']

    if self.dry_run:
      cmd += ['--debug']

    if self.chrome_root:
      cmd.append('--chrome_root=%s' % self.chrome_root)

    if self.pass_revision:
      cmd.append(WithProperties('--chrome_version=%(revision)s'))

    #TODO(petermayo): This adds an empty parameter when not clobbering; fix.
    cmd.append(WithProperties('%s', 'clobber:+--clobber'))

    return cmd


  def add_perf_step(self, params, perf_file, perf_base_url, perf_output_dir):
    """Adds step for uploading perf results using the given file.

    Args:
      params: Extra parameters for cbuildbot.
      perf_file: Name of the perf file to upload. Note the name of this file
        will be used as the testname and params[0] will be used as the platform
        name.
      perf_base_url: If set, base url to build into references.
      perf_output_dir: If set, where the perf files are to update.
    """
    # Name of platform is always taken as the first param.
    platform = params.split()[0]
    # Name of the test is based off the name of the file.
    test = os.path.splitext(perf_file)[0]
    # Assuming all perf files will be stored in the cbuildbot log directory.
    perf_file_path = os.path.join(self.buildroot, 'cbuildbot_logs', perf_file)
    if not perf_base_url:
      perf_base_url = config.Master.perf_base_url
    if not perf_output_dir:
      perf_output_dir = config.Master.perf_output_dir

    report_link = '/'.join([perf_base_url, platform, test,
                            config.Master.perf_report_url_suffix])
    output_dir = chromium_utils.AbsoluteCanonicalPath('/'.join([
        perf_output_dir, platform, test]))

    cmd = ['cat', perf_file_path]

    # Hmm - I wonder how dry_run should affect this.
    perf_class = commands.CreatePerformanceStepClass(
        process_log.GraphingLogProcessor,
        report_link=report_link, output_dir=output_dir,
        factory_properties={}, perf_name=platform,
        test_name=test)

    self.f_cbuild.addStep(
        perf_class, command=cmd, name='Upload Perf Results',
        description='upload_perf_results')

