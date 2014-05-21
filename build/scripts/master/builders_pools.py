# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implement builder selection algorithm."""

try:
  # 0.7.12
  # pylint: disable=E0611,F0401
  from buildbot.scheduler import BadJobfile
except ImportError:
  # 0.8.x
  # pylint: disable=E0611,F0401
  from buildbot.schedulers.trysched import BadJobfile


class BuildersPools(object):
  """A collection of per project pools of builders."""

  def __init__(self, default_pool_name, parent=None):
    self.default_pool_name = default_pool_name
    self.parent = parent
    self.pools = {}
    self._builder_names = None

  def ListBuilderNames(self):
    if not self._builder_names:
      # Flatten and remove duplicates.
      builder_names = set()
      for pool in self.pools:
        builder_names.update(self.pools[pool])
      self._builder_names = list(builder_names)
    return self._builder_names

  def SetParent(self, parent):
    self.parent = parent

  def __getitem__(self, pool_name):
    """This class is usable as a dict of lists."""
    if pool_name not in self.pools:
      self.pools[pool_name] = []
    self._builder_names = None
    return self.pools[pool_name]

  def Select(self, builder_names=None, pool_name=None):
    """Select builders."""
    # If the user has requested specific builders, use those.
    if builder_names:
      return builder_names

    # self.parent is of type TryJob.
    # self.parent.parent is of type buildbot.schedulers.SchedulerManager.
    # self.parent.parent.master is of type buildbot.master.BuildMaster.
    # self.parent.parent.master.botmaster is of type buildbot.master.BotMaster.
    botmaster = self.parent.parent.master.botmaster
    # Collect the set of connected builders.
    available = set([name for name in self.ListBuilderNames()
                     if name in botmaster.builders])

    # Fall back on default pool name.
    if not pool_name:
      pool_name = self.default_pool_name

    # Now for the pool requested, select the available bots.
    pool_builders = self.pools.get(pool_name, [])
    builders = dict((i, []) for i in pool_builders if i in available)

    if not builders:
      # If no builder are available, throw a BadJobfile exception since we
      # can't select a group.
      raise BadJobfile('No builder could be found to run the try job')

    return builders
