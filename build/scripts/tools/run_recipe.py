#!/usr/bin/python -u
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This allows easy execution of a recipe (scripts/slave/recipes, etc.)
without buildbot.

This is currently useful for testing recipes locally while developing them.

Example:
  ./run_recipe.py run_presubmit repo_name=tools_build issue=12345 \
      patchset=1 description="this is a cool description" \
      blamelist=['dude@chromium.org'] \
      rietveld=https://codereview.chromium.org

  This would execute the run_presubmit recipe, passing
  {'repo_name':'tools_build', 'issue':'12345' ...} as properties.

This script can be run from any directory.

See scripts/slave/annotated_run.py for more information about recipes.
"""

import ast
import json
import os
import subprocess
import sys

SCRIPT_PATH = os.path.abspath(os.path.dirname(__file__))
ROOT_PATH = os.path.abspath(os.path.join(SCRIPT_PATH, os.pardir, os.pardir))
SLAVE_DIR = os.path.join(ROOT_PATH, 'slave', 'fake_slave', 'build')

RUNIT = os.path.join(SCRIPT_PATH, 'runit.py')
ANNOTATED_RUN = os.path.join(ROOT_PATH, 'scripts', 'slave', 'annotated_run.py')

def usage(msg=None):
  """Print help and exit."""
  if msg:
    print 'Error:', msg

  print(
"""
usage: %s <recipe_name> [<property=value>*]
""" % os.path.basename(sys.argv[0]))
  sys.exit(bool(msg))


def parse_args(argv):
  """Parses the commandline arguments and returns type-scrubbed
  properties."""
  if len(argv) <= 1:
    usage('Must specify a recipe.')
  bad_parms = [x for x in argv[2:] if ('=' not in x and x != '--')]
  if bad_parms:
    usage('Got bad arguments %s (expecting key=value pairs)' % bad_parms)

  props = dict(x.split('=', 1) for x in argv[2:])

  for key, val in props.iteritems():
    try:
      props[key] = ast.literal_eval(val)
    except (ValueError, SyntaxError):
      pass

  props['recipe'] = argv[1]

  return props


def main(argv):
  props = parse_args(argv)
  props.setdefault('use_mirror', False)

  if not os.path.exists(SLAVE_DIR):
    os.makedirs(SLAVE_DIR)

  env = os.environ.copy()
  env['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'
  env['PYTHONUNBUFFERED'] = '1'
  env['PYTHONIOENCODING'] = 'UTF-8'
  return subprocess.call(
      ['python', '-u', RUNIT, 'python', '-u', ANNOTATED_RUN,
       '--keep-stdin',  # so that pdb works for local execution
       '--factory-properties', json.dumps(props),
       '--build-properties', json.dumps(props)],
      cwd=SLAVE_DIR,
      env=env)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
