# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Skia-specific utilities for setting up build masters."""


from buildbot.scheduler import Scheduler
from buildbot.scheduler import Triggerable
from common import chromium_utils
from common.skia import builder_name_schema
from master import master_utils
from master import slaves_list
from master.builders_pools import BuildersPools
from master.factory import annotator_factory
from master.gitiles_poller import GitilesPoller
from master.skia import status_json
from master.try_job_rietveld import TryJobRietveld

import collections
import config


DEFAULT_AUTO_REBOOT = False
DEFAULT_DO_TRYBOT = True
DEFAULT_RECIPE = 'skia/skia'
POLLING_SCHEDULER_NAME = 'skia'
POLLING_BRANCH = 'master'
TRY_SCHEDULER_NAME = 'try_job_rietveld_skia'
TRY_SCHEDULER_PROJECT = 'skia'


def SetupBuildersAndSchedulers(c, builders, slaves, ActiveMaster):
  """Set up builders and schedulers for the build master."""
  # List of dicts for every builder.
  builder_dicts = []

  # Builder names by scheduler type.
  polling_builders = []
  trybots = []
  # Maps a triggering builder to its triggered builders.
  triggered_builders = collections.defaultdict(list)

  def process_builder(builder, is_trybot=False):
    """Create a dict for the given builder and place its name in the
    appropriate scheduler list.
    """
    builder_name = builder['name']
    if is_trybot:
      builder_name = builder_name_schema.TrybotName(builder_name)

    # Categorize the builder based on its role.
    try:
      category = builder_name_schema.DictForBuilderName(builder_name)['role']
    except ValueError:
      # Assume that all builders whose names don't play by our rules are named
      # upstream and are therefore canaries.
      category = builder_name_schema.BUILDER_ROLE_CANARY

    builder_dict = {
      'name': builder_name,
      'gatekeeper': builder.get('gatekeeper_categories', ''),
      'auto_reboot': builder.get('auto_reboot', DEFAULT_AUTO_REBOOT),
      'slavenames': slaves.GetSlavesName(builder=builder['name']),
      'category': category,
      'recipe': builder.get('recipe', DEFAULT_RECIPE),
    }
    builder_dicts.append(builder_dict)

    parent_builder = builder.get('triggered_by')
    if parent_builder is not None:
      if is_trybot:
        parent_builder = builder_name_schema.TrybotName(parent_builder)
      triggered_builders[parent_builder].append(builder_name)
    elif is_trybot:
      trybots.append(builder_name)
    else:
      polling_builders.append(builder_name)

  # Create builders and trybots.
  for builder in builders:
    process_builder(builder)
    if builder.get('do_trybot', DEFAULT_DO_TRYBOT):
      process_builder(builder, is_trybot=True)

  # Verify that all parent builders exist.
  all_nontriggered_builders = set(polling_builders).union(set(trybots))
  trigger_parents = set(triggered_builders.keys())
  nonexistent_parents = trigger_parents - all_nontriggered_builders
  if nonexistent_parents:
    raise Exception('Could not find parent builders: %s' %
                    ', '.join(nonexistent_parents))

  # Create the schedulers.
  def trigger_name(parent_builder):
    """Given a parent builder name, return a triggerable scheduler name."""
    return 'triggers_%s' % parent_builder

  s = Scheduler(name=POLLING_SCHEDULER_NAME,
                branch=POLLING_BRANCH,
                treeStableTimer=60,
                builderNames=polling_builders)
  c['schedulers'] = [s]

  for parent, builders_to_trigger in triggered_builders.iteritems():
    c['schedulers'].append(Triggerable(name=trigger_name(parent),
                                       builderNames=builders_to_trigger))

  pools = BuildersPools(TRY_SCHEDULER_NAME)
  pools[TRY_SCHEDULER_NAME].extend(trybots)
  c['schedulers'].append(TryJobRietveld(
        name=TRY_SCHEDULER_NAME,
        code_review_sites={TRY_SCHEDULER_PROJECT:
                               ActiveMaster.code_review_site},
        pools=pools,
        project=TRY_SCHEDULER_PROJECT,
        filter_master=True))

  # Create the BuildFactorys.
  annotator = annotator_factory.AnnotatorFactory()

  for builder_dict in builder_dicts:
    triggers = ([trigger_name(builder_dict['name'])]
                if builder_dict['name'] in triggered_builders else None)
    builder_dict['factory'] = annotator.BaseFactory(builder_dict['recipe'],
                                                    triggers=triggers)

  # Finished!
  c['builders'] = builder_dicts


def SetupMaster(ActiveMaster):
  # Buildmaster config dict.
  c = {}

  config.DatabaseSetup(c, require_dbconfig=ActiveMaster.is_production_host)

  ####### CHANGESOURCES

  # Polls config.Master.trunk_url for changes
  poller = GitilesPoller(
      repo_url=ActiveMaster.repo_url,
      branches=['master'],
      pollInterval=10,
      revlinktmpl='https://skia.googlesource.com/skia/+/%s')

  c['change_source'] = [poller]

  ####### SLAVES

  # Load the slave list. We need some information from it in order to
  # produce the builders.
  slaves = slaves_list.SlavesList('slaves.cfg', ActiveMaster.project_name)

  ####### BUILDERS

  # Load the builders list.
  builders = chromium_utils.ParsePythonCfg('builders.cfg')['builders']

  # Configure the Builders and Schedulers.
  SetupBuildersAndSchedulers(c=c, builders=builders, slaves=slaves,
                             ActiveMaster=ActiveMaster)

  ####### BUILDSLAVES

  # The 'slaves' list defines the set of allowable buildslaves. List all the
  # slaves registered to a builder. Remove dupes.
  c['slaves'] = master_utils.AutoSetupSlaves(c['builders'],
                                             config.Master.GetBotPassword())
  master_utils.VerifySetup(c, slaves)

  ####### STATUS TARGETS

  c['buildbotURL'] = ActiveMaster.buildbot_url

  # Adds common status and tools to this master.
  master_utils.AutoSetupMaster(c, ActiveMaster,
      public_html='../master.chromium/public_html',
      templates=['../master.chromium/templates'],
      tagComparator=poller.comparator,
      enable_http_status_push=ActiveMaster.is_production_host,
      order_console_by_time=True,
      console_repo_filter=ActiveMaster.repo_url,
      console_builder_filter=lambda b: not builder_name_schema.IsTrybot(b))

  with status_json.JsonStatusHelper() as json_helper:
    json_helper.putChild('trybots', status_json.TryBuildersJsonResource)

  return c

