# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Native-Client-AddIn-specific BuildFactory.

Based on gclient_factory.py."""

import posixpath

from master.factory import gclient_factory
from master import chromium_step

import config


class NativeClientAddInFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the nacl.sdk master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform
  CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  def __init__(self, build_dir, target_platform=None,
               branch='trunk'):
    solutions = []
    self.target_platform = target_platform
    nacl_sdk_url = posixpath.join(config.Master.nacl_sdk_root_url,
                                  branch, 'src')
    main = gclient_factory.GClientSolution(nacl_sdk_url)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)


  def NativeClientAddInFactory(self, target='Release', clobber=True,
                               tests=None, mode=None,
                               slave_type='BuilderTester', options=None,
                               compile_timeout=1200, build_url=None,
                               factory_properties=None,
                               official_release=False):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)

    # Duplicated from commands.py.. since _python is private them
    if self._target_platform == 'win32':
      # Steps run using a separate copy of python.exe, so it can be killed at
      # the start of a build. But the kill_processes (taskkill) step has to use
      # the original python.exe, or it kills itself.
      python = 'python_slave'
    else:
      python = 'python'

    factory.addStep(chromium_step.AnnotatedCommand,
        name='compile',
        timeout=compile_timeout,
        description='Building NaCl AddIn',
        workdir='build/src/visual_studio/NativeClientVSAddIn',
        haltOnFailure=True,
        command=[python, 'buildbot_run.py'])

    return factory


class NativeClientGameFactory(NativeClientAddInFactory):
  def __init__(self, build_dir, target_platform=None,
             branch='trunk'):
    NativeClientAddInFactory.__init__(self, build_dir, target_platform,
                                      branch)

  def NativeClientGameFactory(self, target='Release', clobber=True, tests=None,
                              mode=None, slave_type='BuilderTester',
                              options=None, compile_timeout=1200,
                              build_url=None, factory_properties=None,
                              official_release=False):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)

    # Duplicated from commands.py.. since _python is private them
    if self._target_platform == 'win32':
      # Steps run using a separate copy of python.exe, so it can be killed at
      # the start of a build. But the kill_processes (taskkill) step has to use
      # the original python.exe, or it kills itself.
      python = 'python_slave'
    else:
      python = 'python'

    factory.addStep(chromium_step.AnnotatedCommand,
        name='compile',
        timeout=compile_timeout,
        description='Building NaCl Game',
        workdir='build/src/nacltoons',
        haltOnFailure=True,
        command=[python, 'buildbot_run.py'])

    return factory
