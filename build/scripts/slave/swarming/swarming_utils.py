# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Code to find swarming_client."""

import os
import sys

from common import find_depot_tools  # pylint: disable=W0611

# From depot_tools/
import subprocess2


OS_MAPPING = {
    'darwin': 'Mac',
    'linux2': 'Linux',
    # TODO(maruel): This solves our immediate need of running all the swarming
    # tests by default on Win7 but this doesn't fix the usage on the CI for XP
    # and Vista.
    'win32': 'Windows-6.1',
}


# This should match build/scripts/master/factory/swarming_factory.py until the
# code there is deleted.
# The goal here is to take ~5m of actual test run per shard, e.g. the 'RunTest'
# section in the logs, so that the trade-off of setup time overhead vs latency
# is reasonable. The overhead is in the 15~90s range, with the vast majority
# being downloading the executable files. While it can be lowered, it'll stay in
# the "few seconds" range due to the sheer size of the executables to map.
# Anything not listed defaults to 1 shard.
TESTS_SHARDS = {
    'browser_tests': 5,
    'interactive_ui_tests': 3,
    'sync_integration_tests': 4,
    'unit_tests': 2,
}


def find_client(base_dir):
  """Returns the path to swarming_client if found.

  |base_dir| will be in general os.getcwd(), so the script is very dependent on
  CWD. CWD should be the base directory of the checkout. It has always been the
  case.
  """
  src_swarming_client = os.path.join(
      base_dir, 'src', 'tools', 'swarming_client')
  if os.path.isdir(src_swarming_client):
    return src_swarming_client

  # This is the previous path. This can be removed around 2013-12-01.
  src_swarm_client = os.path.join(base_dir, 'src', 'tools', 'swarm_client')
  if os.path.isdir(src_swarm_client):
    return src_swarm_client


def get_version(client):
  """Returns the version of swarming.py client tool as a tuple, if available."""
  try:
    version = subprocess2.check_output(
        [
          sys.executable,
          os.path.join(client, 'swarming.py'),
          '--version',
        ])
  except (subprocess2.CalledProcessError, OSError):
    return None
  version = tuple(map(int, version.split('.')))
  print('Detected swarming.py version %s' % '.'.join(map(str, version)))
  return version


def build_to_priority(build_properties):
  """Returns the Swarming task priority for the build.

  Does this by determining the build type. Lower is higher priority.
  """
  url = build_properties.get('buildbotURL', '')
  # TODO(maruel): It's a tad annoying to use the url as a signal here. It is
  # just too easy to forget to update this list so find a way to specify the
  # priority more clearly.
  ci_masters = (
      '/chromium/',
      '/chromium.chrome/',
      '/chromium.chromiumos/',
      '/chromium.linux/',
      '/chromium.mac/',
      '/chromium.memory/',
      '/chromium.win/',
  )
  try_masters = (
      '/tryserver.chromium.linux/',
      '/tryserver.chromium.mac/',
      '/tryserver.chromium.win/',
      '/tryserver.nacl/',
  )

  if url.endswith(ci_masters):
    # Continuous integration master.
    return 10

  if url.endswith(try_masters):
    requester = build_properties.get('requester')
    if requester == 'commit-bot@chromium.org':
      # Commit queue job.
      return 30
    # Normal try job.
    return 50

  # FYI builder or something else we do not know about. Run these at very low
  # priority so if something is misconfigured above, we can catch it sooner.
  return 200
