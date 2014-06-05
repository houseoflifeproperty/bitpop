# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client Ports specific commands. Based on commands.py"""

from master import chromium_step
from master.factory import commands

import config

class NativeClientPortsCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Where to point waterfall links for builds and test results.
    self._archive_url = config.Master.archive_url

    # Where the slave scripts are.
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._build_dir = self.PathJoin('build', build_dir)

    self._cygwin_env = {
      'PATH': (
        'c:\\cygwin\\bin;'
        'c:\\cygwin\\usr\\bin;'
        'c:\\WINDOWS\\system32;'
        'c:\\WINDOWS;'
        'e:\\b\depot_tools;'
      ),
    }
    self._runhooks_env = None
    self._build_compile_name = 'compile'
    self._gyp_build_tool = None
    self._build_env = {}
    self._repository_root = ''
    if target_platform.startswith('win'):
      self._build_env['PATH'] = (
          r'c:\cygwin\bin;'
          r'c:\native_client_sdk\third_party\cygwin\bin;'
          r'c:\WINDOWS\system32;'
          r'c:\WINDOWS;'
          r'e:\b\depot_tools;'
          r'e:\b\depot_tools\python275_bin;'
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

    if self._target_platform.startswith('win'):
      self.script_prefix = 'set PWD=&& '
      self.script_suffix = '.cmd'
    else:
      self.script_prefix = './'
      self.script_suffix = '.sh'

  def AddAnnotatedStep(self, timeout=1200):
    build_script = '%sbuildbot_selector%s' % (
        self.script_prefix, self.script_suffix)
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotate',
                          description='annotate',
                          timeout=timeout,
                          workdir='build/src/build_tools',
                          env=self._build_env,
                          haltOnFailure=True,
                          command=build_script)
