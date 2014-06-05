# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Native-Client-Ports-specific BuildFactory.

Based on gclient_factory.py."""

from master.factory import gclient_factory
from master.factory import nacl_ports_commands

import config


class NativeClientPortsFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the naclports master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  def __init__(self, build_dir, target_platform=None, use_supplement=False,
               alternate_url=None, name=None):
    solutions = []
    self.target_platform = target_platform
    nacl_ports_url = config.Master.nacl_ports_url
    if alternate_url:
      nacl_ports_url = alternate_url
    main = gclient_factory.GClientSolution(
        nacl_ports_url,
        name=name,
        needed_components=self.NEEDED_COMPONENTS)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)

  def NativeClientPortsFactory(self, slave_type='BuilderTester',
                               timeout=1200, target='Release',
                               factory_properties=None, official_release=False):
    factory_properties = factory_properties or {}
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec()
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    nacl_ports_cmd_obj = nacl_ports_commands.NativeClientPortsCommands(
        factory,
        target,
        self._build_dir,
        self._target_platform)

    # Add one annotate step and do everything in the annotator.
    nacl_ports_cmd_obj.AddAnnotatedStep(timeout=timeout)

    return factory
