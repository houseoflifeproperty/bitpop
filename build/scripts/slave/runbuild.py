#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Execute buildsteps on the slave.

This is the buildrunner, a script designed to run builds on the slave. It works
by mocking out the structures of a Buildbot master, then running a slave under
that 'fake' master. There are several benefits to this approach, the main one
being that build code can be changed and reloaded without a master restart.

Usage is detailed with -h.
"""

# pylint: disable=C0323

import optparse
import re
import os
import sys
import time

# Bootstrap PYTHONPATH from runit
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
from tools import runit
runit.add_build_paths(sys.path)

from common import master_cfg_utils
from common import chromium_utils
from slave import builder_utils
from slave import runbuild_utils


def get_args():
  """Process command-line arguments."""

  prog_desc = 'Executes a Buildbot build locally, without a master.'
  usage = '%prog [options] <master directory> [builder or slave hostname]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--list-masters', action='store_true',
                    help='list masters in search path')
  parser.add_option('--master-dir', help='specify a master directory '
                    'instead of a mastername')
  parser.add_option('--list-builders', help='list all available builders for '
                    'this master', action='store_true')
  parser.add_option('-s', '--slavehost', metavar='slavehost',
                    help='specify a slavehost to operate as')
  parser.add_option('-b', '--builder', metavar='builder',
                    help='string specified is a builder name')
  parser.add_option('--list-steps', action='store_true',
                    help='list steps in factory, but don\'t execute them')
  parser.add_option('--show-commands', action='store_true',
                    help='when listing steps, also show the generated output'
                         ' command. Also enables --list-steps and '
                         '--override-brdostep.')
  parser.add_option('--override-brdostep', action='store_true',
                    help='process all steps, even those with '
                         'brDoStepIf=False or None.')
  parser.add_option('--stepfilter', help='only run steps that match the '
                    'stepfilter regex')
  parser.add_option('--stepreject', help='reject any steps that match the '
                    'stepfilter regex')
  parser.add_option('--logfile', default='build_runner.log',
                    help='log build runner output to file (use - for stdout). '
                    'default: %default')
  parser.add_option('--hide-header', help='don\'t log environment information'
                    ' to logfile', action='store_true')
  parser.add_option('--slave-dir', help='location of the slave dir',
                    default=None)
  parser.add_option('--svn-rev', help='revision to check out, default: '
                    'LKGR')
  parser.add_option('--master-cfg', default='master.cfg',
                    help='filename of the master config. default: %default')
  parser.add_option('--builderpath',
                    help='directory to build results in. default: safe '
                    'transformation of builder name')
  parser.add_option('--build-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='build properties in JSON format')
  parser.add_option('--factory-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='factory properties in JSON format')
  parser.add_option('--output-build-properties', action='store_true',
                    help='output JSON-encoded build properties extracted from'
                    ' the build')
  parser.add_option('--output-factory-properties', action='store_true',
                    help='output JSON-encoded build properties extracted from'
                    'the build factory')
  parser.add_option('--annotate', action='store_true',
                    help='format output to work with the Buildbot annotator')
  parser.add_option('--test-config', action='store_true',
                    help='Attempt to parse all builders and steps without '
                    'executing them. Returns 0 on success.')
  parser.add_option('--fail-fast', action='store_true',
                    help='Exit on first step error instead of continuing.')

  return parser.parse_args()


def args_ok(inoptions, pos_args):
  """Verify arguments are correct and prepare args dictionary."""

  if inoptions.factory_properties:
    for key in inoptions.factory_properties:
      setattr(inoptions, key, inoptions.factory_properties[key])

  if inoptions.list_masters:
    return True

  if inoptions.build_properties and not inoptions.master_dir:
    if inoptions.build_properties['mastername']:
      inoptions.mastername = inoptions.build_properties['mastername']
    else:
      print >>sys.stderr, 'Error: build properties did not specify a ',
      print >>sys.stderr, 'mastername.'
      return False
  else:
    if not (inoptions.master_dir or pos_args):
      print >>sys.stderr, 'Error: you must provide a mastername or ',
      print >>sys.stderr, 'directory.'
      return False
    else:
      if not inoptions.master_dir:
        inoptions.mastername = pos_args.pop(0)

  inoptions.step_regex = None
  inoptions.stepreject_regex = None
  if inoptions.stepfilter:
    if inoptions.stepreject:
      print >>sys.stderr, ('Error: can\'t specify both stepfilter and '
                           'stepreject at the same time.')
      return False

    try:
      inoptions.step_regex = re.compile(inoptions.stepfilter)
    except re.error as e:
      print >>sys.stderr, 'Error compiling stepfilter regex \'%s\': %s' % (
          inoptions.stepfilter, e)
      return False
  if inoptions.stepreject:
    if inoptions.stepfilter:
      print >>sys.stderr, ('Error: can\'t specify both stepfilter and '
                           'stepreject at the same time.')
      return False
    try:
      inoptions.stepreject_regex = re.compile(inoptions.stepreject)
    except re.error as e:
      print >>sys.stderr, 'Error compiling stepreject regex \'%s\': %s' % (
          inoptions.stepreject, e)
      return False

  if inoptions.list_builders:
    return True

  if inoptions.show_commands:
    inoptions.override_brdostep = True
    inoptions.list_steps = True

  if inoptions.test_config:
    inoptions.spec = {}
    inoptions.revision = 12345
    inoptions.build_properties['got_revision'] = 12345
    inoptions.build_properties['revision'] = 12345
    return True

  if inoptions.build_properties and not (inoptions.slavehost or
                                         inoptions.builder):
    if inoptions.build_properties['buildername']:
      inoptions.builder = inoptions.build_properties['buildername']
    else:
      print >>sys.stderr, 'Error: build properties did not specify a '
      print >>sys.stderr, 'buildername.'
      return False
  else:
    if not (pos_args or inoptions.slavehost or inoptions.builder):
      print >>sys.stderr, 'Error: you must provide a builder or slave hostname.'
      return False

  # buildbot expects a list here, not a comma-delimited string
  if 'blamelist' in inoptions.build_properties:
    inoptions.build_properties['blamelist'] = (
        inoptions.build_properties['blamelist'].split(','))

  inoptions.spec = {}
  if inoptions.builder:
    inoptions.spec['builder'] = inoptions.builder
  elif inoptions.slavehost:
    inoptions.spec['hostname'] = inoptions.slavehost
  else:
    inoptions.spec['either'] = pos_args.pop(0)

  if inoptions.logfile == '-' or inoptions.annotate:
    inoptions.log = sys.stdout
  else:
    try:
      inoptions.log = open(inoptions.logfile, 'w')
    except IOError as err:
      errno, strerror = err
      print >>sys.stderr, 'Error %d opening logfile %s: %s' % (
          inoptions.logfile, errno, strerror)
      return False
    print >>sys.stderr, 'Writing to logfile', inoptions.logfile

  inoptions.revision = None
  if inoptions.build_properties and not inoptions.svn_rev:
    if inoptions.build_properties.get('revision'):
      try:
        inoptions.revision = int(inoptions.build_properties['revision'])
      except ValueError:
        inoptions.revision = None

    # got_revision will supersede revision if present.
    if inoptions.build_properties.get('got_revision'):
      try:
        inoptions.revision = int(inoptions.build_properties['got_revision'])
      except ValueError:
        inoptions.revision = None

    if not inoptions.revision:
      print >>sys.stderr, ('Error: build properties did not specify '
                           'valid revision.')
      return False

    if inoptions.revision < 1:
      print >>sys.stderr, 'Error: revision must be a non-negative integer.'
      return False

    print >>sys.stderr, 'using revision: %d' % inoptions.revision
    inoptions.build_properties['revision'] = '%d' % inoptions.revision
  else:
    if inoptions.svn_rev:
      try:
        inoptions.revision = int(inoptions.svn_rev)
      except ValueError:
        inoptions.revision = None

      if not inoptions.revision or inoptions.revision < 1:
        print >>sys.stderr, 'Error: svn rev must be a non-negative integer.'
        return False

      if not inoptions.annotate:
        print >>sys.stderr, 'using revision: %d' % inoptions.revision
    else:  # nothing specified on command line, let's check LKGR
      inoptions.revision, errmsg = chromium_utils.GetLKGR()
      if not inoptions.revision:
        print >>sys.stderr, errmsg
        return False
      if not inoptions.annotate:
        print >>sys.stderr, 'using LKGR: %d' % inoptions.revision

  return True


def execute(options):
  if options.list_masters:
    masterpairs = master_cfg_utils.GetMasters()
    master_cfg_utils.PrettyPrintMasters(masterpairs)
    return 0

  if options.master_dir:
    config = master_cfg_utils.LoadConfig(options.master_dir, options.master_cfg)
  else:
    path = master_cfg_utils.ChooseMaster(options.mastername)
    if not path:
      return 2

    config = master_cfg_utils.LoadConfig(path, config_file=options.master_cfg)

  if not config:
    return 2

  mastername = config['BuildmasterConfig']['properties']['mastername']
  builders = config['BuildmasterConfig']['builders']
  options.build_properties.update(config['BuildmasterConfig'].get(
      'properties', {}))

  if options.list_builders:
    master_cfg_utils.PrettyPrintBuilders(builders, mastername)
    return 0

  if options.test_config:
    for builder in builders:
      # We need to provide a slavename, so just pick the first one
      # the builder has.
      builder['slavename'] = builder['slavenames'][0]
      execute_builder(builder, mastername, options)
    return 0

  my_builder = master_cfg_utils.ChooseBuilder(builders, options.spec)
  return execute_builder(my_builder, mastername, options)

def execute_builder(my_builder, mastername, options):
  if options.spec and 'hostname' in options.spec:
    slavename = options.spec['hostname']
  elif (options.spec and 'either' in options.spec) and (
      options.spec['either'] != my_builder['name']):
    slavename = options.spec['either']
  else:
    slavename = my_builder['slavename']

  if not my_builder:
    return 2

  buildsetup = options.build_properties
  if 'revision' not in buildsetup:
    buildsetup['revision'] = '%d' % options.revision
  if 'branch' not in buildsetup:
    buildsetup['branch'] = 'src'

  steplist, build = builder_utils.MockBuild(my_builder, buildsetup, mastername,
      slavename, basepath=options.builderpath,
      build_properties=options.build_properties,
      slavedir=options.slave_dir)

  if options.output_build_properties:
    print
    print 'build properties:'
    print runbuild_utils.PropertiesToJSON(build.getProperties())

  if options.output_factory_properties:
    print
    print 'factory properties:'
    print runbuild_utils.PropertiesToJSON(my_builder['factory'].properties)

  if options.output_build_properties or options.output_factory_properties:
    return 0

  commands = builder_utils.GetCommands(steplist)
  if options.test_config:
    return 0

  if options.override_brdostep:
    for command in commands:
      command['doStep'] = True

  filtered_commands = runbuild_utils.FilterCommands(commands,
                                                    options.step_regex,
                                                    options.stepreject_regex)

  if options.list_steps:
    print
    print 'listing steps in %s/%s:' % (mastername, my_builder['name'])
    print
    for skip, cmd in filtered_commands:
      if 'command' not in cmd:
        print '-', cmd['name'], '[skipped] (custom step type: %s)' % (
            cmd['stepclass'])
      elif skip:
        print '-', cmd['name'], '[skipped]'
      elif skip is None:
        print '-', cmd['name'], '[skipped] (not under buildrunner)'
      else:
        print '*', cmd['name'],
        if options.show_commands:
          print '(in %s): %s' % (cmd['quoted_workdir'], cmd['quoted_command'])
        print
    return 0

  # Only execute commands that can be executed.
  filtered_commands = [(s, c) for s, c in filtered_commands if 'command' in c]

  if not options.annotate:
    print >>sys.stderr, 'using %s builder \'%s\'' % (mastername,
        my_builder['name'])

  start_time = time.clock()
  commands_executed, err = runbuild_utils.Execute(filtered_commands,
      options.annotate, options.log, fail_fast=options.fail_fast)
  end_time = time.clock()

  if err:
    print >>sys.stderr, ('error occurred in previous step, aborting! (%0.2fs'
                         ' since start).' % (end_time - start_time))
    return 2

  if not options.annotate:
    print >>sys.stderr, '%d commands completed (%0.2fs).' % (
        commands_executed, end_time - start_time)
  else:
    if commands_executed < 1:
      print '0 commands executed.'
  return 0


def main():
  opts, args = get_args()
  if not args_ok(opts, args):
    print
    print 'run with --help for usage info'
    return 1

  retcode = execute(opts)

  if retcode == 0:
    if not (opts.annotate or opts.list_masters or opts.list_builders
            or opts.list_steps or opts.test_config):
      print >>sys.stderr, 'build completed successfully'
  else:
    if not opts.annotate:
      print >>sys.stderr, 'build error encountered! aborting build'

  return retcode


if __name__ == '__main__':
  sys.exit(main())
