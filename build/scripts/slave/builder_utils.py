#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=F0401

"""Routines to extract step information from builders.

This module mocks out enough of a Buildbot build system to extract BuildSteps
from builders. This is useful if you want to use these Buildsteps separate from
a Buildbot master.
"""

# pylint: disable=C0323,R0201

import os
import re
import sys

from common import chromium_utils

# slaves are currently set to buildbot 0.7, while masters to 0.8
# these are required to override 0.7 and are necessary until slaves
# have been transitioned to 0.8
chromium_utils.AddThirdPartyLibToPath('buildbot_8_4p1', override=True)
chromium_utils.AddThirdPartyLibToPath('buildbot_slave_8_4', override=True)
chromium_utils.AddThirdPartyLibToPath('twisted_10_2', override=True)
chromium_utils.AddThirdPartyLibToPath('sqlalchemy_0_7_1', override=True)
chromium_utils.AddThirdPartyLibToPath('sqlalchemy_migrate_0_7_1', override=True)
chromium_utils.AddThirdPartyLibToPath('jinja2', override=True)
chromium_utils.AddThirdPartyLibToPath('decorator_3_3_1', override=True)
chromium_utils.AddThirdPartyLibToPath('requests_1_2_3', override=True)

from buildbot.process import base
from buildbot.process import builder as real_builder
from buildbot.process.properties import Properties
from buildbot.status import build as build_module
from buildbot.status import builder
from buildbot.status.results import EXCEPTION
from buildbot.status.results import FAILURE
import buildbot.util
from buildslave.commands import registry
from buildslave.runprocess import shell_quote
from twisted.internet import defer
from twisted.internet import reactor
from twisted.python.reflect import accumulateClassList
from twisted.python.reflect import namedModule
from twisted.spread import pb
from twisted.spread import util


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class FakeChange(object):
  """Represents a mock of a change to the source tree. See
  http://buildbot.net/buildbot/docs/0.8.5/reference/buildbot.changes.changes.
  Change-class.html for what I'm really supposed to be."""

  properties = Properties()
  who = 'me'


class FakeSource(object):
  """A mocked-up SourceStamp, which encapsulates all the parameters of the
  source checkout to build. See http://buildbot.net/buildbot/docs/latest/
  reference/buildbot.sourcestamp.SourceStamp-class.html for reference."""

  def __init__(self, setup):
    self.revision = setup.get('revision')
    self.branch = setup.get('branch')
    self.repository = setup.get('repository')
    self.project = setup.get('project')
    self.patch = setup.get('patch')
    self.changes = [FakeChange()]

    if not self.branch: self.branch = None
    if not self.revision:
      raise ValueError('must specify a revision!')


class FakeRequest(object):
  """A mocked-up BuildRequest, which encapsulates the parameters of the build.
  See http://buildbot.net/buildbot/docs/0.8.6/reference/buildbot.process.
  buildrequest.BuildRequest-class.html for reference."""

  reason = 'Because'
  properties = Properties()

  def __init__(self, buildargs):
    self.source = FakeSource(buildargs)

  def mergeWith(self, others):
    return self.source

  def mergeReasons(self, others):
    return self.reason


class FakeSlave(util.LocalAsRemote):
  """A mocked combination of BuildSlave and SlaveBuilder. Controls the build
  by kicking off steps and receiving messages as those steps run. See
  http://buildbot.net/buildbot/docs/0.7.12/reference/buildbot.slave.bot.
  SlaveBuilder-class.html and http://buildbot.net/buildbot/docs/0.8.3/
  reference/buildbot.buildslave.BuildSlave-class.html for reference."""

  def __init__(self, builddir, slavebuilddir, slavename):
    self.slave = self
    self.properties = Properties()
    self.slave_basedir = '.'
    self.basedir = '.'  # this must be '.' since I combine slavebuilder
                        # and buildslave
    self.path_module = namedModule('posixpath')
    self.slavebuilddir = slavebuilddir or builddir
    self.builddir = builddir
    self.slavename = slavename
    self.usePTY = True
    self.updateactions = []
    self.unicode_encoding = 'utf8'
    self.command = None
    self.remoteStep = None

  def addUpdateAction(self, action):
    self.updateactions.append(action)

  def getSlaveCommandVersion(self, command, oldversion=None):
    return command

  def sendUpdate(self, data):
    for action in self.updateactions:
      action(data)
    self.remoteStep.remote_update([[data, 0]])

  def messageReceivedFromSlave(self):
    return None

  def sync_startCommand(self, stepref, stepId, command, cmdargs):
    try:
      cmdfactory = registry.getFactory(command)
    except KeyError:
      raise UnknownCommand("unrecognized SlaveCommand '%s'" % command)

    self.command = cmdfactory(self, stepId, cmdargs)

    self.remoteStep = stepref
    d = self.command.doStart()
    d.addCallback(stepref.remote_complete)
    return d


class UnknownCommand(pb.Error):
  """Represent an unknown slave command."""
  pass


class ReturnStatus(object):
  """Singleton needed for global return code."""

  def __init__(self):
    self.code = 0


def buildException(status, why):
  """Output error and stop further steps."""
  print >>sys.stderr, 'build error encountered:', why
  print >>sys.stderr, 'aborting build'
  status.code = 1
  reactor.callFromThread(reactor.stop)


def finished():
  """Tear down twisted session."""
  print >>sys.stderr, 'build completed successfully'
  reactor.callFromThread(reactor.stop)


def startNextStep(steps, run_status, prog_args):
  """Run the next step, optionally skipping if there is a stepfilter."""

  def getNextStep():
    if not steps:
      return None
    return steps.pop(0)
  try:
    s = getNextStep()
    if hasattr(prog_args, 'step_regex'):
      while s and not prog_args.step_regex.search(s.name):
        print >>sys.stderr, 'skipping step: ' + s.name
        s = getNextStep()
    if hasattr(prog_args, 'stepreject_regex'):
      while s and prog_args.stepreject_regex.search(s.name):
        print >>sys.stderr, 'skipping step: ' + s.name
        s = getNextStep()
  except StopIteration:
    s = None
  if not s:
    return finished()

  print >>sys.stderr, 'performing step: ' + s.name,
  s.step_status.stepStarted()
  d = defer.maybeDeferred(s.startStep, s.buildslave)
  d.addCallback(lambda x: checkStep(x, steps,
                                    run_status, prog_args))
  d.addErrback(lambda x: buildException(run_status, x))
  return d


def checkStep(rc, steps, run_status, prog_args):
  """Check if the previous step succeeded before continuing."""

  if (rc == FAILURE) or (rc == EXCEPTION):
    buildException(run_status, 'previous command failed')
  else:
    defer.maybeDeferred(lambda x: startNextStep(x,
                                                run_status, prog_args), steps)


def ListSteps(my_factory):
  """Construct a list of steps from the builder's factory."""
  steps = []
  stepnames = {}

  for factory, cmdargs in my_factory.steps:
    cmdargs = cmdargs.copy()
    try:
      step = factory(**cmdargs)
    except:
      print >>sys.stderr, ('error while creating step, factory=%s, args=%s'
                           % (factory, cmdargs))
      raise
    name = step.name
    if name in stepnames:
      count = stepnames[name]
      count += 1
      stepnames[name] = count
      name = step.name + ('_%d' % count)
    else:
      stepnames[name] = 0
    step.name = name

    # workdir is often silently passed through
    if 'workdir' in cmdargs:
      step.workdir = cmdargs['workdir']

    #TODO: is this a bug in FileUpload?
    if not hasattr(step, 'description') or not step.description:
      step.description = [step.name]
    if not hasattr(step, 'descriptionDone') or not step.descriptionDone:
      step.descriptionDone = [step.name]

    step.locks = []
    steps.append(step)

  return steps


class FakeMaster:
  def __init__(self, mastername):
    self.db = None
    self.master_name = mastername
    self.master_incarnation = None


class FakeBotmaster:
  def __init__(self, mastername, properties=Properties()):
    self.master = FakeMaster(mastername)
    self.parent = self
    self.properties = properties


def process_steps(steplist, build, buildslave, build_status, basedir):
  """Attach build and buildslaves to each step."""
  for step in steplist:
    step.setBuild(build)
    step.setBuildSlave(buildslave)
    step.setStepStatus(build_status.addStepWithName(step.name))
    step.setDefaultWorkdir(os.path.join(basedir, 'build'))
    if not hasattr(step, 'workdir') or not step.workdir:
      step.workdir = os.path.join(basedir, 'build')

    if not os.path.isabs(step.workdir):
      step.workdir = os.path.join(basedir, step.workdir)


def StripBuildrunnerIgnore(step):
  assert not step.name.endswith('_buildrunner_ignore_1'), (
      'Duplicate buildrunner step %s not allowed in %s' % (
          step.name.rstrip('_buildrunner_ignore_1'), step.build.builder.name))
  step.name = re.sub('_buildrunner_ignore$', '', step.name)


def GetCommands(steplist):
  """Extract shell commands from a step.

  Take the BuildSteps from MockBuild() and, if they inherit from ShellCommand,
  renders any renderables and extracts out the actual shell command to be
  executed. Returns a list of command hashes.
  """
  commands = []
  for step in steplist:
    cmdhash = {}
    StripBuildrunnerIgnore(step)
    cmdhash['name'] = step.name
    cmdhash['doStep'] = None
    cmdhash['stepclass'] = '%s.%s' % (step.__class__.__module__,
                                      step.__class__.__name__)
    if hasattr(step, 'command'):
      # None signifies this is not a buildrunner-added step.
      if step.brDoStepIf is None:
        doStep = step.brDoStepIf
      # doStep may modify build properties, so it must run before rendering.
      elif isinstance(step.brDoStepIf, bool):
        doStep = step.brDoStepIf
      else:
        doStep = step.brDoStepIf(step)

      renderables = []
      accumulateClassList(step.__class__, 'renderables', renderables)

      for renderable in renderables:
        setattr(step, renderable, step.build.render(getattr(step,
                renderable)))

      cmdhash['doStep'] = doStep
      cmdhash['command'] = step.command
      cmdhash['quoted_command'] = shell_quote(step.command)
      cmdhash['workdir'] = step.workdir
      cmdhash['quoted_workdir'] = shell_quote([step.workdir])
      cmdhash['haltOnFailure'] = step.haltOnFailure
      if hasattr(step, 'env'):
        cmdhash['env'] = step.env
      else:
        cmdhash['env'] = {}
      if hasattr(step, 'timeout'):
        cmdhash['timeout'] = step.timeout
      if hasattr(step, 'maxTime'):
        cmdhash['maxTime'] = step.maxTime

      cmdhash['description'] = step.description
      cmdhash['descriptionDone'] = step.descriptionDone
    commands.append(cmdhash)
  return commands


def MockBuild(my_builder, buildsetup, mastername, slavename, basepath=None,
              build_properties=None, slavedir=None):
  """Given a builder object and configuration, mock a Buildbot setup around it.

  This sets up a mock BuildMaster, BuildSlave, Build, BuildStatus, and all other
  superstructure required for BuildSteps inside the provided builder to render
  properly. These BuildSteps are returned to the user in an array. It
  additionally returns the build object (in order to get its properties if
  desired).

  buildsetup is passed straight into the FakeSource's init method and
  contains sourcestamp information (revision, branch, etc).

  basepath is the directory of the build (what goes under build/slave/, for
  example 'Chromium_Linux_Builder'. It is nominally inferred from the builder
  name, but it can be overridden. This is useful when pointing the buildrunner
  at a different builder than what it's running under.

  build_properties will update and override build_properties after all
  builder-derived defaults have been set.
  """

  my_factory = my_builder['factory']
  steplist = ListSteps(my_factory)

  build = base.Build([FakeRequest(buildsetup)])
  safename = buildbot.util.safeTranslate(my_builder['name'])

  my_builder.setdefault('builddir', safename)
  my_builder.setdefault('slavebuilddir', my_builder['builddir'])


  workdir_root = None
  if not slavedir:
    workdir_root = os.path.join(SCRIPT_DIR, '..', '..', 'slave',
                                my_builder['slavebuilddir'])

  if not basepath: basepath = safename
  if not slavedir: slavedir = os.path.join(SCRIPT_DIR,
                                           '..', '..', 'slave')
  basedir = os.path.join(slavedir, basepath)
  build.basedir = basedir
  if not workdir_root:
    workdir_root = basedir

  builderstatus = builder.BuilderStatus('test')
  builderstatus.basedir = basedir
  buildnumber = build_properties.get('buildnumber', 1)
  builderstatus.nextBuildNumber = buildnumber + 1

  mybuilder = real_builder.Builder(my_builder, builderstatus)
  build.setBuilder(mybuilder)
  build_status = build_module.BuildStatus(builderstatus, buildnumber)

  build_status.setProperty('blamelist', [], 'Build')
  build_status.setProperty('mastername', mastername, 'Build')
  build_status.setProperty('slavename', slavename, 'Build')
  build_status.setProperty('gtest_filter', [], 'Build')
  build_status.setProperty('extra_args', [], 'Build')
  build_status.setProperty('build_id', buildnumber, 'Build')

  # if build_properties are passed in, overwrite the defaults above:
  buildprops = Properties()
  if build_properties:
    buildprops.update(build_properties, 'Botmaster')
  mybuilder.setBotmaster(FakeBotmaster(mastername, buildprops))

  buildslave = FakeSlave(safename, my_builder.get('slavebuilddir'), slavename)
  build.build_status = build_status
  build.setupSlaveBuilder(buildslave)
  build.setupProperties()
  process_steps(steplist, build, buildslave, build_status, workdir_root)

  return steplist, build
