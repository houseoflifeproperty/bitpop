#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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
    self._target_platform = target_platform
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
    if not is_dartc and not is_dart2dart:
      cmd += ' --arch=%s' % (options['arch'])
      cmd += ' runtime'

    if is_dart2dart:
      cmd += ' create_sdk'
    self._factory.addStep(shell.ShellCommand,
                          name='build',
                          description='build',
                          timeout=timeout,
                          env = self._custom_env,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=cmd)

  def AddTests(self, options=None, timeout=1200):
    options = options or {}
    is_dartc = (options.get('name') != None and
                options.get('name').startswith('dartc'))
    is_dart2dart = (options.get('name') != None and
                    options.get('name').startswith('dart2dart'))

    arch = options.get('arch')
    if is_dartc:
      compiler = 'dartc'
      runtime = 'none'
      configuration = (options['mode'], arch, compiler, runtime)
      base_cmd = ('python ' + self._tools_dir + '/test.py '
                  ' --progress=line --report --time --mode=%s --arch=%s '
                  ' --compiler=%s --runtime=%s') % configuration
    elif is_dart2dart:
      compiler = 'dart2dart'
      runtime = 'vm'
      # TODO(ricow): Remove shard functionality when we move to annotated.
      shards = 1
      shard = 1
      if options.get('shards') != None and options.get('shard') != None:
        shards = options['shards']
        shard = options['shard']
      configuration = (options['mode'], arch, compiler, shards, shard)
      base_cmd = ('python ' + self._tools_dir + '/test.py '
                  ' --progress=buildbot --report --time --mode=%s --arch=%s '
                  ' --compiler=%s --shards=%s --shard=%s') % configuration
    else:
      compiler = 'none'
      runtime = 'vm'
      configuration = (options['mode'], arch, compiler, runtime)
      base_cmd = ('python ' + self._tools_dir + '/test.py '
                  ' --progress=line --report --time --mode=%s --arch=%s '
                  ' --compiler=%s --runtime=%s') % configuration

    if is_dartc:
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles={"flakylog": ".flaky.log"},
                            lazylogfiles=True)
    elif is_dart2dart:
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles={"flakylog": ".flaky.log"},
                            lazylogfiles=True)
      cmd = base_cmd + ' --minified'
      self._factory.addStep(shell.ShellCommand,
                            name='minified tests',
                            description='minified tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles={"flakylog": ".flaky.log"},
                            lazylogfiles=True)
    else:
      if options.get('flags') != None:
        base_cmd += options.get('flags')
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles={"flakylog": ".flaky.log"},
                            lazylogfiles=True)
      # Rerun all tests in checked mode (assertions and type tests).
      cmd = base_cmd + ' --checked'
      self._factory.addStep(shell.ShellCommand,
                            name='checked_tests',
                            description='checked_tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles={"flakylog": ".flaky.log"},
                            lazylogfiles=True)

  def AddAnnotatedSteps(self, python_script, timeout=1200):
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotated_steps',
                          description='annotated_steps',
                          timeout=timeout,
                          haltOnFailure=True,
                          env = self._custom_env,
                          workdir=self._dart_build_dir,
                          command=[self._python, python_script],
                          logfiles={"flakylog": ".flaky.log"},
                          lazylogfiles=True)
