#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Downgrades buildsteps in a directory of pickled buildbot builds.

  Buildbot archives builds by pickling them and storing basic versioning
  information. When the master is upgraded to a new persistenceVersion (see
  third_party/buildbot_8_4p1/buildbot/status/buildstep.py), the master will
  automatically update all pickled builds to the latest version. Buildbot
  provides no way to downgrade back to a previous persistenceVersion, which is
  what this script attempts to do.

  It's important to note that this file only modifies the buildsteps inside of a
  pickled build, and that builds themselves have their own persistence version
  which is unrelated.

  For a list of command-line options, call this script with '--help'.
"""

import cPickle
import optparse
import os
import re
import shutil
import sys

from common import master_cfg_utils


if True:
  print 'This script is disabled. It should not be run by anyone.'
  sys.exit(1)


def process_options():
  """Process options from the command line."""
  prog_desc = 'Downgrade buildsteps in a directory of pickled builds.'
  usage = '%prog [options] [master name or filename]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--list-masters', action='store_true',
                    help='list masters in search path')
  parser.add_option('--master-dir', help='specify a master directory '
                                         'instead of a mastername')
  parser.add_option('-t', '--target-version', default=None, type='int',
                    help='downgrade to specified version')
  parser.add_option('--commit', action='store_true',
                    help='save downgraded results on top of old files. leaving '
                    'out this option is equivalent to a dry-run')
  parser.add_option('--builder-name', default='builder',
                    help='filename for builder')

  options, args = parser.parse_args()

  if len(args) > 1:
    parser.error('too many arguments specified!')

  options.filename = None
  options.mastername = None

  if args:
    if os.path.exists(args[0]):
      options.filename = args[0]
      options.builderpath = os.path.join(os.path.dirname(args[0]),
                                         options.builder_name)
    else:
      options.mastername = args[0]
  return options


def loadBuilder(path):
  """Load a pickled builder from a filename."""
  with open(path, 'rb') as pkl_file:
    builder = cPickle.load(pkl_file)
  return builder


def loadBuild(path, builder):
  """Load a pickled build from a filename."""
  # adapted from loadBuildFromFile() in buildbot/status/builder.py
  with open(path, 'rb') as pkl_file:
    build = cPickle.load(pkl_file)
    build.builder = builder
    for step in build.getSteps():
      step.builder = builder
      for loog in step.getLogs():
        loog.builder = builder
  return build


def getBuildStepVersion(step):
  """Return the unpickled builder's persistenceVersion.

  The version reported in buildstep.persistenceVersion is what the currently
  loaded version of buildbot expects a step to be (instead of what is pickled).
  This returns what has been pickled.
  """
  return getattr(step,
                 'buildbot.status.builder.BuildStepStatus.persistenceVersion')


def downgrade(build, toVersion):
  """Perform a downgrade option in-memory."""
  maxVersion = 4  # the maximum version we understand
  minVersion = 3  # the minimum version we understand

  if toVersion > maxVersion or toVersion < minVersion:
    raise ValueError('Requested downgrade to version %d, only %d - %d '
                     ' supported.' % (toVersion, minVersion, maxVersion))

  for step in build.getSteps():
    pV = getBuildStepVersion(step)
    if pV > maxVersion or pV < minVersion:
      raise ValueError('Buildsteps in build %d are persistence version %d, only'
                       ' %d - %d  supported.' % (step.getNumber(), pV,
                                                 minVersion, maxVersion))
    if toVersion < 4 and step.persistenceVersion == 4:
      del step.hidden
      step.persistenceVersion = 3
      setattr(step,
              'buildbot.status.builder.BuildStepStatus.persistenceVersion',
              3)


def processBuild(filename, builder, options):
  """Processes a build file, returning if the operation was successful."""
  try:
    build = loadBuild(filename, builder)

  except IOError as e:
    print '   Error %d loading %s: %s' % (e.errno, filename, e.strerror)
    return False

  if not options.target_version:
    steps = build.getSteps()
    if not steps:
      print '   Build %d at version <none> --  %s' % (build.getNumber(),
                                                      filename)
    else:
      print '   Build %d at version %d --  %s' % (build.getNumber(),
                                                  getBuildStepVersion(steps[0]),
                                                  filename)
  else:
    try:
      downgrade(build, options.target_version)
    except ValueError as e:
      print '   Error downgrading build %d: %s -- %s' % (build.getNumber(), e,
                                                         filename)
      return False
    if options.commit:
      shutil.copy(filename, filename + '.bak')
      with open(filename, 'wb') as output:
        cPickle.dump(build, output, -1)
      os.remove(filename + '.bak')
    print ('   Buildsteps for build %d downgraded to version %d'
           ' -- %s' % (build.getNumber(), options.target_version, filename))
  return True


def locateBuilderDirs(path, options):
  """Find all candidate builder dirs under a master."""
  dirs = [os.path.join(path, f) for f in os.listdir(path) if
          os.path.isdir(os.path.join(path, f))]
  builders = [os.path.relpath(f) for f in dirs
              if options.builder_name in os.listdir(f)]
  return builders


def processDirectory(path, options):
  """Process all builds found in a directory."""
  print 'in dir %s:' % path
  builder = loadBuilder(os.path.join(path, options.builder_name))
  builds = [os.path.join(path, f) for f in os.listdir(path)
            if re.match('^\d+$', f)]
  if not builds:
    print '   no builds'
  for build in builds:
    if not processBuild(build, builder, options):
      return False
  return True


def main(options):
  if options.list_masters:
    masterpairs = master_cfg_utils.GetMasters()
    master_cfg_utils.PrettyPrintMasters(masterpairs)
    return 0

  if options.master_dir:
    path = options.master_dir
  elif options.mastername:
    path = master_cfg_utils.ChooseMaster(options.mastername)
    if not path:
      return 2
  else:
    path = options.filename

  if os.path.isdir(path):
    print path
    for directory in locateBuilderDirs(path, options):
      if not processDirectory(directory, options):
        if not options.commit:
          print
          print '*** errors encountered but commit was not set '
        return 2
    if not options.commit:
      print
      print '*** re-run with --commit to overwrite changes ***'
  else:
    builder = loadBuilder(options.builderpath)
    if not processBuild(path, builder, options):
      if not options.commit:
        print
        print '*** errors encountered but commit was not set '
      return 2
    if not options.commit:
      print
      print '*** re-run with --commit to overwrite changes ***'
  return 0


if __name__ == '__main__':
  sys.exit(main(process_options()))
