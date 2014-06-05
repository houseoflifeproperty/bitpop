#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to list builder slaves and trigger dependencies.

  Buildsystem capacity simulations require knowledge of builder->slave mappings
  as well as which builds are triggered off of each other. This script provides
  that capability.

  Example usage: `scripts/tools/runit.py python scripts/tools/build_topology.py
                      masters/master.tryserver.chromium`
"""

import collections
import json
import optparse
import sys

from common import master_cfg_utils
from buildbot import schedulers
from buildbot import steps


USAGE = '%s [options] master_dir' % sys.argv[0]


def get_topology_info(master_dir):
  config = master_cfg_utils.LoadConfig(master_dir)['BuildmasterConfig']

  triggers = {}
  for s in config['schedulers']:
    if isinstance(s, schedulers.triggerable.Triggerable):
      triggers[s.name] = s.builderNames

  builders = collections.defaultdict(dict)
  for b in config['builders']:
    # Add the slaves to the builder entry.
    builders[b['name']]['slaves'] = b['slavenames']

    # Find trigger steps, see which scheduler they trigger, and flatten that to
    # the list of builders triggered by this builder.
    builder_trigger = set()
    for step in b['factory'].steps:
      if step[0] == steps.trigger.Trigger:
        for scheduler in step[1]['schedulerNames']:
          builder_trigger |= set(triggers[scheduler])
    builders[b['name']]['triggers'] = list(builder_trigger)

  return builders


def main():
  option_parser = optparse.OptionParser(usage=USAGE)
  _, args = option_parser.parse_args()

  if not args:
    option_parser.error('must specify a master directory!')
    return 1
  if len(args) > 1:
    option_parser.error('must specify only one master directory!')

  builder_info = get_topology_info(args[0])
  print json.dumps(builder_info)
  return 0

if '__main__' == __name__:
  sys.exit(main())
