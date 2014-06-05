# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Native-Client-SDK-specific BuildFactory.

Based on gclient_factory.py."""

import posixpath

from master.factory import gclient_factory
from master.factory import nacl_sdk_commands

import config


class NativeClientSDKFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the nacl.sdk master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform
  CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)
  CUSTOM_VARS_SOURCEFORGE_URL = ('sourceforge_url',
                                 config.Master.sourceforge_url)
  CUSTOM_VARS_WEBKIT_MIRROR = ('webkit_trunk', config.Master.webkit_trunk_url)

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  def __init__(self, build_dir, target_platform=None, use_supplement=False,
               alternate_url=None, branch='trunk'):
    solutions = []
    self.target_platform = target_platform
    nacl_sdk_url = posixpath.join(config.Master.nacl_sdk_root_url,
                                  branch, 'src')
    if alternate_url:
      nacl_sdk_url = alternate_url
    main = gclient_factory.GClientSolution(
        nacl_sdk_url,
        custom_vars_list=[self.CUSTOM_VARS_WEBKIT_MIRROR,
                          self.CUSTOM_VARS_GOOGLECODE_URL,
                          self.CUSTOM_VARS_SOURCEFORGE_URL],
        custom_deps_list=[('src/pdf', None),
                          ('src-pdf', None)],
        needed_components=self.NEEDED_COMPONENTS)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)


  def NativeClientSDKFactory(self, target='Release', clobber=False, tests=None,
                             mode=None, slave_type='BuilderTester',
                             options=None, compile_timeout=1200, build_url=None,
                             factory_properties=None, official_release=True):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    nacl_sdk_cmd_obj = nacl_sdk_commands.NativeClientSDKCommands(
        factory,
        target,
        self._build_dir,
        self._target_platform)

    # Add the compile step if needed.
    nacl_sdk_cmd_obj.AddPrepareSDKStep()

    return factory
