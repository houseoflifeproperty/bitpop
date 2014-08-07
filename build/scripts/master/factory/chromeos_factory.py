# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

import os

from buildbot.steps import shell
from buildbot.process.properties import Property, WithProperties

from master import chromium_step
from master.factory import build_factory
from master.factory import chromeos_build_factory


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
      max_time: Max overall time from the start before the command is killed.
  """
  _default_git_base = 'https://chromium.googlesource.com/chromiumos'
  _default_chromite = _default_git_base + '/chromite.git'
  _default_max_time = 16 * 60 * 60

  def __init__(self, script, params=None, b_params=None, timeout=9000,
               branch='master', chromite_repo=_default_chromite,
               factory=None, use_chromeos_factory=False, slave_manager=True,
               chromite_patch=None, sleep_sync=None,
               show_gclient_output=True, max_time=_default_max_time):
    if chromite_patch:
      assert ('url' in chromite_patch and 'ref' in chromite_patch)

    self.branch = branch
    self.chromite_patch = chromite_patch
    self.chromite_repo = chromite_repo
    self.timeout = timeout
    self.show_gclient_output = show_gclient_output
    self.slave_manager = slave_manager
    self.sleep_sync = sleep_sync
    self.step_args = {}
    self.step_args['maxTime'] = max_time

    if factory:
      self.f_cbuild = factory
    elif use_chromeos_factory:
      # Suppresses revisions, at the moment.
      self.f_cbuild = chromeos_build_factory.BuildFactory()
    else:
      self.f_cbuild = build_factory.BuildFactory()

    self.chromite_dir = None
    self.add_bootstrap_steps()
    if script:
      self.add_chromite_step(script, params, b_params)

  def git_clear_and_checkout(self, repo, patch=None):
    """Clears and clones the given git repo. Returns relative path to repo.

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

    return git_checkout_dir

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

    self.chromite_dir = self.git_clear_and_checkout(self.chromite_repo,
                                                    self.chromite_patch)

  def add_chromite_step(self, script, params, b_params, legacy=False):
    """Adds a step that runs a chromite command.

    Args:
      script:  Name of the script to run from chromite/bin.
      params:  A string containing extra parameters for the script.
      b_params:  An array of StepParameters.
      legacy:  Use a different directory for some legacy invocations.
    """
    script_subdir = 'buildbot' if legacy else 'bin'
    cmd = ['%s/%s/%s' % (self.chromite_dir, script_subdir, script)]
    if b_params:
      cmd.extend(b_params)
    if params:
      cmd.extend(params.split())

    self.f_cbuild.addStep(chromium_step.AnnotatedCommand,
                          command=cmd,
                          timeout=self.timeout,
                          name=script,
                          description=script,
                          usePTY=False,
                          **self.step_args)

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
      dry_run: Don't push anything as we're running a test run.
      trybot: Whether this is creating builders for the trybot waterfall.
      chrome_root: The place to put or use the chrome source.
      pass_revision: to pass the chrome revision desired into the build.
      legacy_chromite: If set, ask chromite to use an older cbuildbot directory.
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
               legacy_chromite=False,
               **kwargs):
    super(CbuildbotFactory, self).__init__(None, None,
        use_chromeos_factory=not pass_revision, **kwargs)

    self.script = script
    self.trybot = trybot
    self.chrome_root = chrome_root
    self.pass_revision = pass_revision
    self.legacy_chromite = legacy_chromite
    self.buildroot = buildroot
    self.dry_run = dry_run

    if params:
      self.add_cbuildbot_step(params)


  def add_cbuildbot_step(self, params):
    self.add_chromite_step(self.script, params, self.compute_buildbot_params(),
                           legacy=self.legacy_chromite)


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


class ChromitePlusFactory(ChromiteFactory):
  """
  Create a build factory that depends on chromite but runs a script from
  another repo.

  Arg Changes from Parent Class:
     script: Instead of pointing to a chromite script, points to a script in the
             additional repo specified. Chromite repo is also checked out and
             included in the PYTHONPATH to called script.
     chromite_plus_repo: Repo that script resides in.
     buildroot: buildroot to set. Default /b/cbuild.
     dry_run: Don't push anything as we're running a test run.
  """
  def __init__(self, script, chromite_plus_repo,
               buildroot='/b/cbuild',
               dry_run=False,
               *args, **dargs):
    # Initialize without running a script step similar to Cbuildbot factory.
    super(ChromitePlusFactory, self).__init__(None, **dargs)
    self.buildroot = buildroot
    self.dry_run = dry_run

    # Checkout and run the script.
    plus_checkout_dir = self.git_clear_and_checkout(chromite_plus_repo, None)
    self.add_chromite_plus_step(script, plus_checkout_dir)

  def add_chromite_plus_step(self, script, plus_checkout_dir):
    """Adds a step that runs the chromite_plus command.

    Args:
      script:  Name of the script to run from chromite_plus_repo.
      plus_checkout_dir: Directory that script resides in.
    """
    cmd = [os.path.join(plus_checkout_dir, script)]

    # Are we a debug build.
    if self.dry_run:
      cmd.extend(['--debug'])

    # Adds buildroot / clobber as last arg.
    cmd.append(WithProperties('%s' + self.buildroot, 'clobber:+--clobber '))

    self.f_cbuild.addStep(chromium_step.AnnotatedCommand,
                          command=cmd,
                          timeout=self.timeout,
                          name=script,
                          description=script,
                          usePTY=False,
                          env={'PYTHONPATH':'.'},
                          ** self.step_args)
