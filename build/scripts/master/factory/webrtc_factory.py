# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.factory import gclient_factory
from master.factory import chromium_commands

import config


class WebRTCFactory(gclient_factory.GClientFactory):

  CUSTOM_VARS_ROOT_DIR = ('root_dir', 'src')
  # Can't use the same Valgrind constant as in chromium_factory.py, since WebRTC
  # uses another path (use_relative_paths=True in DEPS).
  CUSTOM_DEPS_VALGRIND = ('third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')

  def __init__(self, build_dir, target_platform, svn_root_url, branch,
               custom_deps_list=None):
    """Creates a WebRTC factory.

    This factory can also be used to build stand-alone projects.

    Args:
      build_dir: Directory to perform the build relative to. Usually this is
        trunk/build for WebRTC and other projects.
      target_platform: Platform, one of 'win32', 'darwin', 'linux2'
      svn_root_url: Subversion root URL (i.e. without branch/trunk part).
      branch: Branch name to checkout.
      custom_deps_list: Content to be put in the custom_deps entry of the
        .gclient file for the default solution. The parameter must be a list
        of tuples with two strings in each: path and remote URL.
    """
    svn_url = svn_root_url + branch
    # Use root_dir=src since many Chromium scripts rely on that path.
    custom_vars_list = [self.CUSTOM_VARS_ROOT_DIR]
    solutions = []
    solutions.append(gclient_factory.GClientSolution(
        svn_url, name='src', custom_vars_list=custom_vars_list,
        custom_deps_list=custom_deps_list))
    if config.Master.webrtc_internal_url:
      solutions.append(gclient_factory.GClientSolution(
          config.Master.webrtc_internal_url, name='webrtc-internal',
          custom_vars_list=custom_vars_list))
    self._branch = branch
    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)

  def WebRTCFactory(self, target='Debug', clobber=False, tests=None, mode=None,
                    slave_type='BuilderTester', options=None,
                    compile_timeout=1200, build_url=None, project=None,
                    factory_properties=None, gclient_deps=None, webcam=False):
    options = options or ''
    tests = tests or []
    factory_properties = factory_properties or {}
    _EnsureFastBuild(factory_properties)

    if factory_properties.get('needs_valgrind'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_VALGRIND]
    factory = self.BuildFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties, gclient_deps)

    # Get the factory command object to create new steps to the factory.
    cmds = chromium_commands.ChromiumCommands(factory, target,
                                                 self._build_dir,
                                                 self._target_platform)
    # Override test runner script paths with our own that can run any test and
    # have our suppressions configured.
    cmds._posix_memory_tests_runner = cmds.PathJoin(
        'src', 'tools', 'valgrind-webrtc', 'webrtc_tests.sh')
    cmds._win_memory_tests_runner = cmds.PathJoin(
        'src', 'tools', 'valgrind-webrtc', 'webrtc_tests.bat')

    cmds.AddWebRTCTests(tests, factory_properties)
    return factory


def _EnsureFastBuild(factory_properties):
  '''Ensures fastbuild=1 is set for GYP_DEFINES in the gclient_env.

  If gclient_env key don't exist in factory_properties, it will be created.
  If the GYP_DEFINES key don't exist in the gclient_env dict, it will be
  created.
  '''
  if not 'gclient_env' in factory_properties:
    factory_properties['gclient_env'] = {'GYP_DEFINES': ''}
  if not 'GYP_DEFINES' in factory_properties['gclient_env']:
    factory_properties['gclient_env']['GYP_DEFINES'] = ''
  if 'fastbuild=1' not in factory_properties['gclient_env']['GYP_DEFINES']:
    factory_properties['gclient_env']['GYP_DEFINES'] += ' fastbuild=1'
