#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Dart specific commands. Based on commands.py
"""

from buildbot.steps import shell
from buildbot.process.properties import WithProperties

from master import chromium_step
from master.factory import commands

class DartCommands(commands.FactoryCommands):
  """Encapsulates methods to add dart commands to a buildbot factory."""

  logfiles = {
    "flakylog": ".flaky.log",
    "debuglog": ".debug.log",
    "testoutcomelog": ".test-outcome.log",
  }

  standard_flags = "--write-debug-log --write-test-outcome-log"

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, env=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Two additional directories up compared to normal chromium scripts due
    # to using runtime as runtime dir inside dart directory inside
    # build directory.
    self._script_dir = self.PathJoin('..', self._script_dir)
    self._tools_dir = self.PathJoin('tools')

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._slave_dir = self.PathJoin(self._script_dir,
                                            '..', '..', '..',
                                            'build', 'scripts',
                                            'slave', 'dart')

    self._dart_util = self.PathJoin(self._slave_dir, 'dart_util.py')
    self._dart_build_dir = self.PathJoin('build', 'dart')
    self._repository_root = ''
    self._custom_env = env or {}

  def AddMaybeClobberStep(self, clobber, options=None, timeout=1200):
    """Possibly clobber.

    Either clobber unconditionally (e.g. nuke-and-pave builder, set at
    factory build time), or at runtime (clobber checkbox).  If the
    former, the clobber arg is set.  If the latter, we use a buildbot
    Properties object.

    TODO(jrg); convert into a doStepIf with a closure referencing
    step.build.getProperties().  E.g.
    http://permalink.gmane.org/gmane.comp.python.buildbot.devel/6039
    """
    options = options or {}
    clobber_cmd = [self._python, self._dart_util]
    clobber_cmd.append(WithProperties('%(clobber:+--clobber)s'))
    workdir = self._dart_build_dir
    self._factory.addStep(shell.ShellCommand,
                          name='maybe clobber',
                          description='maybe clobber',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=clobber_cmd)

  # pylint: disable=W0221
  def AddCompileStep(self, options=None, timeout=1200):
    options = options or {}
    cmd = 'python ' + self._tools_dir + '/build.py --mode=%s' % \
        (options['mode'])
    workdir = self._dart_build_dir
    is_dartc = (options.get('name') != None and
                options.get('name').startswith('dartc'))
    is_dart2dart = (options.get('name') != None and
                    options.get('name').startswith('dart2dart'))
    is_new_analyzer = (options.get('name') != None and
                       options.get('name').startswith('new_analyzer'))
    is_analyzer_experimental = (options.get('name') != None and
                                options.get('name')
                                .startswith('analyzer_experimental'))
    is_vm = not (is_dartc or is_dart2dart or is_new_analyzer or
                 is_analyzer_experimental)

    if is_vm:
      cmd += ' --arch=%s' % (options['arch'])
      cmd += ' runtime'
    elif is_dart2dart:
      cmd += ' dart2dart_bot'
    elif is_dartc and options['mode'] == 'debug':
      # For dartc we always do a full build, except for debug mode
      # where we will time out doing api docs.
      cmd += ' dartc_bot'
    else:
      # We don't specify a specific target (i.e. we build the all target)
      pass

    self._factory.addStep(shell.ShellCommand,
                          name='build',
                          description='build',
                          timeout=timeout,
                          env = self._custom_env,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=cmd)

  def AddKillStep(self, step_name='Kill leftover process'):
    cmd = 'python ' + self._tools_dir + '/task_kill.py --kill_browsers=True'
    self._factory.addStep(shell.ShellCommand,
                          name='Taskkill',
                          description=step_name,
                          env = self._custom_env,
                          haltOnFailure=False,
                          workdir=self._dart_build_dir,
                          command=cmd)

  def AddArchiveCoredumps(self, options=None, step_name='Archive coredumps'):
    options = options or {}
    if (options.get('name') != None and
        options.get('name').startswith('vm')):
      cmd = 'python ' + self._tools_dir + '/archive_crash.py'
      self._factory.addStep(shell.ShellCommand,
                            name='ArchiveCore',
                            description=step_name,
                            env = self._custom_env,
                            haltOnFailure=False,
                            workdir=self._dart_build_dir,
                            command=cmd)

  def AddAnalyzerTests(self, options, name, timeout):
    compiler = 'dartanalyzer'
    if name.startswith('analyzer_experimental'):
      compiler = 'dart2analyzer'
    cmd = ('python ' + self._tools_dir + '/test.py '
           ' --progress=line --report --time --mode=%s --arch=%s '
           ' --compiler=%s --runtime=none --failure-summary %s'
           ) % (options['mode'], options['arch'], compiler,
                self.standard_flags)
    self._factory.addStep(shell.ShellCommand,
                          name='tests',
                          description='tests',
                          timeout=timeout,
                          env = self._custom_env,
                          haltOnFailure=False,
                          workdir=self._dart_build_dir,
                          command=cmd,
                          logfiles=self.logfiles,
                          lazylogfiles=True)

  def AddDart2dartTests(self, options, name, timeout):
    shards = options.get('shards') or 1
    shard = options.get('shard') or 1
    cmd = ('python ' + self._tools_dir + '/test.py '
           ' --progress=buildbot --report --time --mode=%s --arch=%s '
           ' --compiler=dart2dart --shards=%s --shard=%s %s'
           ) % (options['mode'], options['arch'], shards, shard,
                self.standard_flags)
    if 'backend' in name:
      cmd += ' --builder-tag=new_backend'
    self._factory.addStep(shell.ShellCommand,
                          name='tests',
                          description='tests',
                          timeout=timeout,
                          env = self._custom_env,
                          haltOnFailure=False,
                          workdir=self._dart_build_dir,
                          command=cmd,
                          logfiles=self.logfiles,
                          lazylogfiles=True)
    cmd += ' --minified'
    self._factory.addStep(shell.ShellCommand,
                          name='minified tests',
                          description='minified tests',
                          timeout=timeout,
                          env = self._custom_env,
                          haltOnFailure=False,
                          workdir=self._dart_build_dir,
                          command=cmd,
                          logfiles=self.logfiles,
                          lazylogfiles=True)

  def AddVMTests(self, options, timeout, channel):
    cmd = ('python ' + self._tools_dir + '/test.py '
           ' --progress=line --report --time --mode=%s --arch=%s '
           '--compiler=none --runtime=vm --failure-summary %s '
           '--copy-coredumps'
           ) % (options['mode'], options['arch'], self.standard_flags)

    vm_options = options.get('vm_options')
    if vm_options:
      cmd += ' --vm-options=%s' % vm_options
    if options.get('flags') != None:
      cmd += options.get('flags')
    if channel and (channel.name == 'be' or channel.name == 'dev'):
      cmd += ' --exclude-suite=pkg'

    checked_config = options.get('checked_config')
    if not checked_config:
      checked_config = 'both'
    if checked_config == 'unchecked' or checked_config == 'both':
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=False,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)
    if checked_config == 'checked' or checked_config == 'both':
      cmd += ' --checked'
      self._factory.addStep(shell.ShellCommand,
                            name='checked_tests',
                            description='checked_tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=False,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)

  def AddTests(self, options=None, timeout=1200, channel=None):
    options = options or {}
    name = options.get('name') or ''
    is_dart2dart = name.startswith('dart2dart')
    is_analyzer = (name.startswith('new_analyzer') or
                   name.startswith('analyzer_experimental'))

    if is_analyzer:
      self.AddAnalyzerTests(options, name, timeout)
    elif is_dart2dart:
      self.AddDart2dartTests(options, name, timeout)
    else:
      self.AddVMTests(options, timeout, channel)

  def AddAnnotatedSteps(self, python_script, timeout=1200, run=1):
    name = 'annotated_steps'
    env = dict(self._custom_env)
    env['BUILDBOT_ANNOTATED_STEPS_RUN'] = '%d' % run
    if run > 1:
      name = name + '_run%d' % run
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name=name,
                          description=name,
                          timeout=timeout,
                          haltOnFailure=False,
                          env=env,
                          workdir=self._dart_build_dir,
                          command=[self._python, python_script],
                          logfiles=self.logfiles,
                          lazylogfiles=True)

  def AddTrigger(self, trigger):
    self._factory.addStep(trigger)

