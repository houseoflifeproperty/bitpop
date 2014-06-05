#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests all master.cfgs to make sure they load properly."""

import collections
import optparse
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from common import chromium_utils
from common import master_cfg_utils

# Masters which do not currently load from the default configuration. These need
# to be fixed and removed from the list!
BLACKLIST = set(['chromium.swarm',
                 ])


Cmd = collections.namedtuple('Cmd', ['name', 'path', 'env'])


def GetMasterCmds(masters, blacklist, pythonpaths):
  assert blacklist <= set(m for m, _ in masters)
  env = os.environ.copy()
  pythonpaths = list(pythonpaths or [])
  buildpaths = ['scripts', 'third_party', 'site_config']
  thirdpartypaths = ['buildbot_8_4p1', 'buildbot_slave_8_4', 'jinja2',
                     'mock-1.0.1', 'twisted_10_2']

  pythonpaths.extend(os.path.join(BASE_DIR, p) for p in buildpaths)
  pythonpaths.extend(os.path.join(BASE_DIR, 'third_party', p)
                     for p in thirdpartypaths)
  if env.get('PYTHONPATH'):
    pythonpaths.append(env.get('PYTHONPATH'))
  env['PYTHONPATH'] = os.pathsep.join(pythonpaths)

  return [Cmd(name, path, env)
      for name, path in masters if name not in blacklist]


def main(argv):
  start_time = time.time()
  parser = optparse.OptionParser()
  parser.add_option('-v', '--verbose', action='store_true')
  options, args = parser.parse_args(argv[1:])
  if args:
    parser.error('Unknown arguments: %s' % args)
  num_skipped = len(BLACKLIST)
  masters_list = GetMasterCmds(
      masters=master_cfg_utils.GetMasters(include_internal=False),
      blacklist=BLACKLIST,
      pythonpaths=None)
  build_internal = os.path.join(BASE_DIR, '..', 'build_internal')
  if os.path.exists(build_internal):
    internal_test_data = chromium_utils.ParsePythonCfg(
        os.path.join(build_internal, 'tests', 'internal_masters_cfg.py'),
        fail_hard=True)
    internal_cfg = internal_test_data['masters_cfg_test']
    num_skipped += len(internal_cfg['blacklist'])
    masters_list.extend(GetMasterCmds(
        masters=master_cfg_utils.GetMasters(include_public=False),
        blacklist=internal_cfg['blacklist'],
        pythonpaths=[os.path.join(build_internal, p)
                     for p in internal_cfg['paths']]))

  with master_cfg_utils.TemporaryMasterPasswords():
    processes = [subprocess.Popen([
      sys.executable, os.path.join(BASE_DIR, 'scripts', 'slave', 'runbuild.py'),
      cmd.name, '--test-config'], stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, env=cmd.env) for cmd in masters_list]
    results = [(proc.communicate()[0], proc.returncode) for proc in processes]

  def GetCommandStr(cmd, cmd_output):
    out = [cmd.path]
    out.extend('>  ' + line for line in cmd_output.splitlines())
    return '\n'.join(out + [''])

  if options.verbose:
    for cmd, (out, code) in zip(masters_list, results):
      # Failures will be printed below
      if code == 0 and out:
        print GetCommandStr(cmd, out)

  failures = [(cmd, out) for cmd, (out, r) in zip(masters_list, results) if r]
  if failures:
    print '\nFAILURE  The following master.cfg files did not load:\n'
    for cmd, out in failures:
      print GetCommandStr(cmd, out)

  test_time = round(time.time() - start_time, 1)
  print 'Parsed %d masters successfully, %d failed, %d skipped in %gs.' % (
      len(masters_list), len(failures), num_skipped, test_time)
  return bool(failures)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
