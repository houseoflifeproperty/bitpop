#!/usr/bin/python -u
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This allows easy execution of a recipe (scripts/slave/recipes, etc.)
without buildbot.

This is currently useful for testing recipes locally while developing them.

Example:

./run_recipe.py run_presubmit repo_name=tools_build issue=12345 patchset=1 \
    description="this is a cool description" blamelist=['dude@chromium.org'] \
    rietveld=https://codereview.chromium.org

Alternatively, the properties can be specified as a Python dict using a
--properties-file, which can optionally be read in from stdin. For example:

./run_recipe.py run_presubmit --properties-file - <<EOF
{
  'repo_name': 'tools_build',
  'issue': 12345,
  'patchset': 1,
  'description': 'this is a cool description',
  'blamelist': ['dude@chromium.org'],
  'rietveld': 'https://codereview.chromium.org',
}
EOF

This would execute the run_presubmit recipe, passing
{'repo_name':'tools_build', 'issue':'12345' ...} as properties.

This script can be run from any directory.

See scripts/slave/annotated_run.py for more information about recipes.
"""

import argparse
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

USAGE = """
%(prog)s <recipe_name [<property=value>*]
%(prog)s <recipe_name> --properties-file <filename>

If specified, the properties file should contain a Python dictionary. If the
filename "-" is used, then the dictionary is read from stdin, for example:

%(prog)s recipe_name --properties-file - <<EOF
{
  'property1: 'value1',
  'property2: 'value2',
}
EOF

This could also be specified as:

%(prog)s <recipe_name> property1=value1 property2=value2
"""


def parse_args(args):
  """Parses the command line arguments and returns type-scrubbed properties."""
  parser = argparse.ArgumentParser(usage=USAGE)
  parser.add_argument('recipe')
  parser.add_argument('--properties-file')
  known_args, extra_args = parser.parse_known_args(args)

  if known_args.properties_file:
    properties = get_properties_from_file(known_args.properties_file)
  else:
    # If properties were given as command line arguments, make sure that
    # they are all prop=value pairs.
    bad_params = [x for x in extra_args if '=' not in x]
    if bad_params:
      parser.error('Error: Got bad arguments: %s' % bad_params)
    properties = get_properties_from_args(extra_args)

  assert type(properties) is dict
  properties['recipe'] = known_args.recipe
  return properties


def get_properties_from_args(args):
  properties = dict(x.split('=', 1) for x in args)
  for key, val in properties.iteritems():
    try:
      properties[key] = ast.literal_eval(val)
    except (ValueError, SyntaxError):
      pass  # If a value couldn't be evaluated, silently ignore it.
  return properties


def get_properties_from_file(filename):
  properties_file = sys.stdin if filename == '-' else open(filename)
  return ast.literal_eval(properties_file.read())


def main(args):
  """Gets the recipe name and properties and runs an annotated run."""
  properties = parse_args(args)
  properties.setdefault('use_mirror', False)

  if not os.path.exists(SLAVE_DIR):
    os.makedirs(SLAVE_DIR)

  # Remove any GYP environment variables for the run.
  env = os.environ.copy()
  for k in env.keys():
    if k.startswith('GYP'):
      del env[k]

  env['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'
  env['PYTHONUNBUFFERED'] = '1'
  env['PYTHONIOENCODING'] = 'UTF-8'

  return subprocess.call(
      ['python', '-u', RUNIT, 'python', '-u', ANNOTATED_RUN,
       '--keep-stdin',  # so that pdb works for local execution
       '--factory-properties', json.dumps(properties),
       '--build-properties', json.dumps(properties)],
      cwd=SLAVE_DIR,
      env=env)


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
