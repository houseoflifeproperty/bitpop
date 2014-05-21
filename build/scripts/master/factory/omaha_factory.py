# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the omaha master BuildFactory's.

Based on gclient_factory.py and adds omaha-specific steps."""

from master.factory import omaha_commands
from master.factory import gclient_factory


class OmahaFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the Omaha master.cfg files."""

  def __init__(self, build_dir='omaha', target_platform='win32'):
    omaha_svn_url =  'http://omaha.googlecode.com/svn/trunk'
    main = gclient_factory.GClientSolution(omaha_svn_url,
                                           name='omaha')
    custom_deps_list = [main]

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)


  def OmahaFactory(self, target='opt-win', tests=None,
                   slave_type='BuilderTester', options=None,
                   factory_properties=None, target_arch=None):
    tests = tests or []
    factory_properties = factory_properties or {}

    gclient_spec = self.BuildGClientSpec()
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties,
                               slave_type=slave_type)

    # Get the factory command object to create new steps to the factory.
    omaha_cmd_obj = omaha_commands.OmahaCommands(factory, target,
                                                 self._build_dir,
                                                 self._target_platform,
                                                 target_arch)

    if (slave_type in ['BuilderTester', 'Builder']):
      omaha_cmd_obj.AddHammer(target, options)

    # We don't support running custom tests yet.
    assert(tests == [])

    return factory
