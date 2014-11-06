#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints information from master_site_config.py

The sole purpose of this program it to keep the crap inside build/ while
we're moving to the new infra/ repository. By calling it, you get access
to some information contained in master_site_config.py for a given master,
as a json string.

Invocation: runit.py get_master_config.py --master-name <master name>
"""

import argparse
import inspect
import json
import logging
import os
import sys

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
# Directory containing build/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
assert os.path.isdir(os.path.join(ROOT_DIR, 'build')), \
       'Script may have moved in the hierarchy'

LOGGER = logging


def get_master_directory(master_name):
  """Given a master name, returns the full path to the corresponding directory.

  This function either returns a path to an existing directory, or None.
  """
  if master_name.startswith('master.'):
    master_name = master_name[7:]

  # Look for the master directory
  for build_name in ('build', 'build_internal'):
    master_path = os.path.join(ROOT_DIR,
                               build_name,
                               'masters',
                               'master.' + master_name)

    if os.path.isdir(master_path):
      return master_path
  return None


def read_master_site_config(master_name):
  """Return a dictionary containing master_site_config

  master_name: name of master whose file to parse

  Return: dict (empty dict if there is an error)
  {'master_port': int()}
  """
  master_path = get_master_directory(master_name)

  if not master_path:
    LOGGER.error('full path for master cannot be determined')
    return {}

  master_site_config_path = os.path.join(master_path, 'master_site_config.py')

  if not os.path.isfile(master_site_config_path):
    LOGGER.error('no master_site_config.py file found in %s' % master_path)
    return {}

  local_vars = {}
  try:
    execfile(master_site_config_path, local_vars)
  except Exception:  # pylint: disable=W0703
    # Naked exceptions are banned by the style guide but we are
    # trying to be resilient here.
    LOGGER.exception("exception occured when exec'ing %s"
                     % master_site_config_path)
    return {}

  for _, symbol in local_vars.iteritems():
    if inspect.isclass(symbol):
      if not hasattr(symbol, 'master_port'):
        continue

      config = {'master_port': symbol.master_port}
      for attr in ('project_name', 'slave_port', 'master_host',
                   'master_port_alt', 'buildbot_url'):
        if hasattr(symbol, attr):
          config[attr] = getattr(symbol, attr)
      return config

  LOGGER.error('No master port found in %s' % master_site_config_path)
  return {}


def get_options(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--master-name', required=True)

  return parser.parse_args(argv)


def main():
  options = get_options(sys.argv[1:])
  config = read_master_site_config(options.master_name)
  print json.dumps(config, indent=2, sort_keys=True)
  return 0


if __name__ == '__main__':
  sys.exit(main())
