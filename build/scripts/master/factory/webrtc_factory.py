# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.factory import chromium_factory
from master.factory import gclient_factory
from master.factory import chromium_commands

import config


class WebRTCFactory(chromium_factory.ChromiumFactory):

  CUSTOM_VARS_ROOT_DIR = ('root_dir', 'src')

  # Can't use the same Valgrind constant as in chromium_factory.py, since WebRTC
  # uses another path (use_relative_paths=True in DEPS).
  CUSTOM_DEPS_VALGRIND = ('third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')
  CUSTOM_DEPS_TSAN_WIN = ('third_party/tsan',
     config.Master.trunk_url + '/deps/third_party/tsan')

  def __init__(self, build_dir, target_platform, nohooks_on_update=False,
               custom_deps_list=None, target_os=None):
    """Creates a WebRTC factory.

    This factory can also be used to build stand-alone projects.

    Args:
      build_dir: Directory to perform the build relative to. Usually this is
        trunk/build for WebRTC and other projects.
      target_platform: Platform, one of 'win32', 'darwin', 'linux2'
      nohooks_on_update: If True, no hooks will be executed in the update step.
      custom_deps_list: List of tuples to override directories in the gclient
        spec.
      target_os: Used to sync down OS-specific dependencies, if specified.
    """
    chromium_factory.ChromiumFactory.__init__(
         self, build_dir, target_platform=target_platform,
         nohooks_on_update=nohooks_on_update, target_os=target_os)

    svn_url = config.Master.webrtc_url + '/trunk'

    custom_deps_list = custom_deps_list or []

    # Use root_dir=src since many Chromium scripts rely on that path.
    custom_vars_list = [self.CUSTOM_VARS_ROOT_DIR]

    # Overwrite solutions of ChromiumFactory since we sync WebRTC, not Chromium.
    self._solutions = []
    self._solutions.append(gclient_factory.GClientSolution(
        svn_url, name='src', custom_deps_list=custom_deps_list,
        custom_vars_list=custom_vars_list))
    if config.Master.webrtc_limited_url:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.webrtc_limited_url, name='webrtc-limited',
          custom_vars_list=custom_vars_list))

  def WebRTCFactory(self, target='Debug', clobber=False, tests=None, mode=None,
                    slave_type='BuilderTester', options=None,
                    compile_timeout=1200, build_url=None, project=None,
                    factory_properties=None, gclient_deps=None):
    options = options or ''
    tests = tests or []
    factory_properties = factory_properties or {}
    factory_properties['gclient_env'] = \
        factory_properties.get('gclient_env', {}).copy()

    if factory_properties.get('needs_valgrind'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_VALGRIND]
    elif factory_properties.get('needs_tsan_win'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_TSAN_WIN]
    elif factory_properties.get('needs_drmemory'):
      if 'drmemory.DEPS' not in [s.name for s in self._solutions]:
        self._solutions.append(gclient_factory.GClientSolution(
            config.Master.trunk_url +
            '/deps/third_party/drmemory/drmemory.DEPS',
            'drmemory.DEPS'))

    # Ensure GYP errors out if files referenced in .gyp files are missing.
    self.ForceMissingFilesToBeFatal(project, factory_properties['gclient_env'])

    factory = self.BuildFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties, gclient_deps)

    # Get the factory command object to create new steps to the factory.
    cmds = chromium_commands.ChromiumCommands(factory, target, self._build_dir,
                                              self._target_platform)
    # Override test runner script paths with our own that can run any test and
    # have our suppressions configured.
    valgrind_script_path = cmds.PathJoin('src', 'tools', 'valgrind-webrtc')
    cmds._posix_memory_tests_runner = cmds.PathJoin(valgrind_script_path,
                                                    'webrtc_tests.sh')
    cmds._win_memory_tests_runner = cmds.PathJoin(valgrind_script_path,
                                                  'webrtc_tests.bat')

    if (self._target_platform == 'win32' and factory_properties.get(
        'syzyasan')):
      cmds.AddWindowsSyzyASanStep()

    # Add check/start step for virtual webcams, if needed.
    if factory_properties.get('virtual_webcam'):
      cmds.AddVirtualWebcamCheck()

    cmds.AddWebRTCTests(tests, factory_properties)
    return factory

