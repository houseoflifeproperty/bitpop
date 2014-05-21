# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities to enable slaves to determine their master without importing any
buildbot or twisted code.
"""

import inspect
import os
import socket
import sys

from common import chromium_utils
import config_bootstrap


def ImportMasterConfigs(master_name=None):
  """Imports master configs.

  Normally a slave can use GetActiveMaster() to find itself and
  determine which ActiveMaster to use.  In that case, the active
  master name is passed in as an arg, and we only load the
  site_config.py that defines it.  When testing, the current "slave"
  won't be found.  In that case, we don't know which config to use, so
  load them all.  In either case, masters are assigned as attributes
  to the config.Master object."""
  for master in chromium_utils.ListMasters():
    path = os.path.join(master, 'master_site_config.py')
    if os.path.exists(path):
      local_vars = {}
      try:
        execfile(path, local_vars)
      # pylint: disable=W0703
      except Exception, e:
        # Naked exceptions are banned by the style guide but we are
        # trying to be resilient here.
        print >> sys.stderr, 'WARNING: cannot exec ' + path
        print >> sys.stderr, e
      for (symbol_name, symbol) in local_vars.iteritems():
        if inspect.isclass(local_vars[symbol_name]):
          setattr(config_bootstrap.Master, symbol_name, symbol)
          # If we have a master_name and it matches, set
          # config_bootstrap.Master.active_master.
          if master_name and master_name == symbol_name:
            setattr(config_bootstrap.Master, 'active_master', symbol)


def GetActiveMaster(slavename=None):
  """Parses all the slaves.cfg and returns the name of the active master
  determined by the host name. Returns None otherwise.

  If a slavename is given, it will be matched against *both* the 'slavename'
  and 'hostname' fields in slave.cfg.  Otherwise, the machine's hostname will be
  matched against only the 'hostname' field.
  """
  if slavename is None:
    config_keys = ['hostname']
    config_val = socket.getfqdn().split('.', 1)[0].lower()
  else:
    config_keys = ['slavename', 'hostname']
    config_val = slavename
  for master in chromium_utils.ListMasters():
    path = os.path.join(master, 'slaves.cfg')
    if os.path.exists(path):
      for slave in chromium_utils.RunSlavesCfg(path):
        for key in config_keys:
          if slave.get(key, None) == config_val:
            return slave['master']
