# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Scheduler
from buildbot.scheduler import Triggerable

import collections

# This file contains useful functions for masters whose slaves run recipes.

def AddSchedulersAndTriggers(buildmaster_config=None,
                             slave_list=None,
                             scheduler_name=None,
                             branch=None):
  """Adds schedulers and triggers to the BuildmasterConfig based on
  the contents of slaves.cfg, passed in as a slave_list.

  This function relies on certain structure in the slaves.cfg, in
  particular the custom 'triggered_by' property, which is not yet
  commonly used to define triggers.

  Returns a dictionary mapping builder name, for those builders which
  invoke triggers, to the (synthesized) name of the trigger.

  TODO(kbr): this function does not yet support builders with
  multiple slaves behind them, but could be updated to do so.

  Throws an Exception if a non-existent builder is mentioned in
  another builder's 'triggered_by' property.

  Arguments:

    buildmaster_config: a BuildmasterConfig into which the
      'schedulers' property will be defined.

    slave_list: a SlavesList constructed from slaves.cfg.

    scheduler_name: the name of the Scheduler for the polling (not
      triggered) builders.
  """
  c = buildmaster_config
  polling_builders = []
  # Maps the parent builder to a set of the names of the builders it triggers.
  trigger_map = collections.defaultdict(list)
  # Maps the name of the parent builder to the (synthesized) name of its
  # trigger, wrapped in a list.
  trigger_name_map = {}
  next_group_id = 0
  for slave in slave_list.slaves:
    builder = slave['builder']
    parent_builder = slave.get('triggered_by')
    if parent_builder is not None:
      if slave_list.GetSlave(builder=parent_builder) is None:
        raise Exception('Could not find parent builder %s for builder %s' %
                        (parent_builder, builder))
      trigger_map[parent_builder].append(builder)
      if parent_builder not in trigger_name_map:
        trigger_name_map[parent_builder] = 'trigger_group_%d' % next_group_id
        next_group_id += 1
    else:
      polling_builders.append(builder)
  s_gpu = Scheduler(name=scheduler_name,
                    branch=branch,
                    treeStableTimer=60,
                    builderNames=polling_builders)
  c['schedulers'] = [s_gpu]
  for name, builders in trigger_map.iteritems():
    c['schedulers'].append(Triggerable(name=trigger_name_map[name],
                                       builderNames=builders))
  return trigger_name_map

def AddRecipeBasedBuilders(buildmaster_config=None,
                           slave_list=None,
                           annotator=None,
                           trigger_name_map=None):
  """Writes builders which use recipes to the BuildmasterConfig's
  'builders' list, using the AnnotatorFactory's BaseFactory.
  Specifies some common factory properties for these builders.

  Arguments:

    buildmaster_config: a BuildmasterConfig into which the
      'builders' property will be defined.

    slave_list: a SlavesList constructed from slaves.cfg.

    annotator: an AnnotatorFactory instance.

    trigger_name_map: the trigger name map returned by
      AddSchedulersAndTriggers, above.
  """
  builders = []
  for slave in slave_list.slaves:
    if 'recipe' in slave:
      factory_properties = {
        'test_results_server': 'test-results.appspot.com',
        'generate_gtest_json': True,
        'build_config': slave['build_config']
      }
      if 'perf_id' in slave:
        factory_properties['show_perf_results'] = True
        factory_properties['perf_id'] = slave['perf_id']
      name = slave['builder']
      builder = {
        'name': name,
        'factory': annotator.BaseFactory(
          slave['recipe'],
          factory_properties,
          [trigger_name_map[name]] if name in trigger_name_map else None)
      }
      # Don't specify auto_reboot unless slaves.cfg does, to let
      # master_utils' default take effect.
      if 'auto_reboot' in slave:
        builder['auto_reboot'] = slave['auto_reboot']
      builders.append(builder)
  buildmaster_config['builders'] = builders
