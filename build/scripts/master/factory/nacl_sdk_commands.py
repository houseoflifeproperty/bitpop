# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client SDK specific commands. Based on commands.py"""

from master import chromium_step
from master.factory import commands


class NativeClientSDKCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Where to point waterfall links for builds and test results.
    self._archive_url = 'http://build.chromium.org/f/client'

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._build_dir = self.PathJoin('build', build_dir)

    self._cygwin_env = {
      'PATH': (
        r'c:\cygwin\bin;'
        r'c:\cygwin\usr\bin;'
        r'c:\WINDOWS\system32;'
        r'c:\WINDOWS;'
        r'e:\b\depot_tools;'
        r'e:\b\depot_tools\python_bin;'
      ),
    }
    self._runhooks_env = None
    self._build_compile_name = 'compile'
    self._gyp_build_tool = None
    self._build_env = {}
    self._repository_root = ''
    if target_platform.startswith('win'):
      self._build_env['PATH'] = (
          r'c:\WINDOWS\system32;'
          r'c:\WINDOWS;'
          r'e:\b\depot_tools;'
          r'e:\b\depot_tools\python_bin;'
          r'c:\Program Files\Microsoft Visual Studio 9.0\VC;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 9.0\VC;'
          r'c:\Program Files\Microsoft Visual Studio 9.0\Common7\Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 9.0\Common7\Tools;'
          r'c:\Program Files\Microsoft Visual Studio 8\VC;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 8\VC;'
          r'c:\Program Files\Microsoft Visual Studio 8\Common7\Tools;'
          r'c:\Program Files (x86)\Microsoft Visual Studio 8\Common7\Tools;'
      )

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin
    s_dir = self._chromium_script_dir

    self._process_dumps_tool = self.PathJoin(self._script_dir,
                                             'process_dumps.py')

    # Scripts in the chromium scripts dir.  This list is sorted by decreasing
    # line length just because it looks pretty.
    self._process_coverage_tool = J(s_dir, 'process_coverage.py')
    self._layout_archive_tool = J(s_dir, 'archive_layout_test_results.py')
    self._crash_handler_tool = J(s_dir, 'run_crash_handler.py')
    self._layout_test_tool = J(s_dir, 'layout_test_wrapper.py')
    self._archive_coverage = J(s_dir, 'archive_coverage.py')
    self._crash_dump_tool = J(s_dir, 'archive_crash_dumps.py')
    self._dom_perf_tool = J(s_dir, 'dom_perf.py')
    self._archive_tool = J(s_dir, 'archive_build.py')
    self._archive_file_tool = J(s_dir, 'archive_file.py')
    self._sizes_tool = J(s_dir, 'sizes.py')

  def AddPrepareSDKStep(self):
    """Adds a step to build the sdk."""

    cmd = ' '.join([self._python,
        'src/native_client_sdk/src/build_tools/nacl-mono-buildbot.py'])
    if self._target_platform.startswith('win'):
      cmd = 'vcvarsall x86 && ' + cmd
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          description='prepare_sdk',
                          timeout=1500,
                          workdir='build',
                          env=self._build_env,
                          haltOnFailure=True,
                          command=cmd)
