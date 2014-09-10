# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import uuid

from buildbot.changes.filter import ChangeFilter
from buildbot.scheduler import Dependent
from buildbot.scheduler import Nightly
from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler as Scheduler
from buildbot.scheduler import Triggerable

from master import slaves_list
from master.url_poller import URLPoller

def GetArchiveUrl(project, machine_name, builder_name, zip_os_name,
                  static_host=None):
  # static host can be used for connections made through an intermediary
  if static_host:
    host = static_host
  else:
    # This is slightly tricky since it depends on os.getcwd() being right.
    slaves = slaves_list.SlavesList('slaves.cfg', project)
    host = slaves.GetSlaveName(project, machine_name)
    if not host:
      raise ValueError("%s isn't reachable" % machine_name)
  return ('http://%s/b/build/slave/%s/chrome_staging/full-build-%s.zip' % (
              host, builder_name, zip_os_name))

def GetGSUtilUrl(gs_bucket, root_folder):
  return 'gs://%s/%s' % (gs_bucket, root_folder)

class Helper(object):
  def __init__(self, defaults):
    self._defaults = defaults
    self._builders = []
    self._factories = {}
    self._schedulers = {}

  def Builder(self, name, factory, gatekeeper=None, scheduler=None,
              builddir=None, auto_reboot=True, notify_on_missing=False,
              slavebuilddir=None, category=None):
    category = category or self._defaults.get('category')
    self._builders.append({'name': name,
                           'factory': factory,
                           'gatekeeper': gatekeeper,
                           'schedulers': scheduler.split('|'),
                           'builddir': builddir,
                           'category': category,
                           'auto_reboot': auto_reboot,
                           'notify_on_missing': notify_on_missing,
                           'slavebuilddir': slavebuilddir})

  def Hourly(self, name, branch, hour='*'):
    """Helper method for the Nightly scheduler."""
    if name in self._schedulers:
      raise ValueError('Scheduler %s already exists' % name)
    self._schedulers[name] = {'type': 'Nightly',
                              'builders': [],
                              'branch': branch,
                              'hour': hour}

  def Periodic(self, name, periodicBuildTimer):
    """Helper method for the Periodic scheduler."""
    if name in self._schedulers:
      raise ValueError('Scheduler %s already exists' % name)
    self._schedulers[name] = {'type': 'Periodic',
                              'builders': [],
                              'periodicBuildTimer': periodicBuildTimer}

  def Dependent(self, name, parent):
    if name in self._schedulers:
      raise ValueError('Scheduler %s already exists' % name)
    self._schedulers[name] = {'type': 'Dependent',
                              'parent': parent,
                              'builders': []}

  def Triggerable(self, name):
    if name in self._schedulers:
      raise ValueError('Scheduler %s already exists' % name)
    self._schedulers[name] = {'type': 'Triggerable',
                              'builders': []}

  def Factory(self, name, factory):
    if name in self._factories:
      raise ValueError('Factory %s already exists' % name)
    self._factories[name] = factory

  def Scheduler(self, name, branch, treeStableTimer=60, categories=None):
    if name in self._schedulers:
      raise ValueError('Scheduler %s already exists' % name)
    self._schedulers[name] = {'type': 'Scheduler',
                              'branch': branch,
                              'treeStableTimer': treeStableTimer,
                              'builders': [],
                              'categories': categories}

  def URLScheduler(self, name, url, pollInterval=300, include_revision=False):
    self._schedulers[name] = {'type': 'URLScheduler',
                              'url': url,
                              'builders': [],
                              'include_revision': include_revision,
                              'pollInterval': pollInterval}

  def Update(self, c):
    global_schedulers = dict((s.name, s) for s in c['schedulers']
                             if s.name.startswith('global_'))
    assert not (set(global_schedulers) & set(self._schedulers))

    for builder in self._builders:
      # Update the schedulers with the builder.
      schedulers = builder['schedulers']
      if schedulers:
        for scheduler in schedulers:
          if scheduler in global_schedulers:
            global_schedulers[scheduler].builderNames.append(builder['name'])
          else:
            self._schedulers[scheduler]['builders'].append(builder['name'])

      # Construct the category.
      categories = []
      if builder.get('category', None):
        categories.append(builder['category'])
      if builder.get('gatekeeper', None):
        categories.extend(builder['gatekeeper'].split('|'))
      category = '|'.join(categories)

      # Append the builder to the list.
      new_builder = {'name': builder['name'],
                     'factory': self._factories[builder['factory']],
                     'category': category,
                     'auto_reboot': builder['auto_reboot']}
      if builder['builddir']:
        new_builder['builddir'] = builder['builddir']
      if builder['slavebuilddir']:
        new_builder['slavebuilddir'] = builder['slavebuilddir']
      c['builders'].append(new_builder)

    # Process the main schedulers.
    for s_name in self._schedulers:
      scheduler = self._schedulers[s_name]
      if scheduler['type'] == 'Scheduler':
        instance = Scheduler(name=s_name,
                             branch=scheduler['branch'],
                             treeStableTimer=scheduler['treeStableTimer'],
                             builderNames=scheduler['builders'],
                             categories=scheduler['categories'])
        scheduler['instance'] = instance
        c['schedulers'].append(instance)
      elif scheduler['type'] == 'URLScheduler':
        ident = str(uuid.uuid4())
        c['change_source'].append(
          URLPoller(changeurl=scheduler['url'],
                    pollInterval=scheduler['pollInterval'],
                    category=ident,
                    include_revision=scheduler['include_revision']))
        instance = Scheduler(name=s_name,
                             change_filter=ChangeFilter(category=ident),
                             builderNames=scheduler['builders'])
        scheduler['instance'] = instance
        c['schedulers'].append(instance)

    # Process the dependent schedulers.
    for s_name in self._schedulers:
      scheduler = self._schedulers[s_name]
      if scheduler['type'] == 'Dependent':
        c['schedulers'].append(
            Dependent(s_name,
                      self._schedulers[scheduler['parent']]['instance'],
                      scheduler['builders']))

    # Process the triggerable schedulers.
    for s_name in self._schedulers:
      scheduler = self._schedulers[s_name]
      if scheduler['type'] == 'Triggerable':
        c['schedulers'].append(Triggerable(s_name,
                                           scheduler['builders']))

    # Process the periodic schedulers.
    for s_name in self._schedulers:
      scheduler = self._schedulers[s_name]
      if scheduler['type'] == 'Periodic':
        c['schedulers'].append(
            Periodic(s_name,
                     periodicBuildTimer=scheduler['periodicBuildTimer'],
                     builderNames=scheduler['builders']))

    # Process the nightly schedulers.
    for s_name in self._schedulers:
      scheduler = self._schedulers[s_name]
      if scheduler['type'] == 'Nightly':
        c['schedulers'].append(Nightly(s_name,
                                       branch=scheduler['branch'],
                                       hour=scheduler['hour'],
                                       builderNames=scheduler['builders']))
