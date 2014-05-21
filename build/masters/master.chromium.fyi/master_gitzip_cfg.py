# -*- mode: python -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from buildbot.scheduler import Nightly
from master.factory.build_factory import BuildFactory
from master.factory import commands
from buildbot.steps import shell

def Update(config, active_master, c):
  factory = BuildFactory()
  factory_commands = commands.FactoryCommands(factory)
  factory_commands.AddUpdateScriptStep()
  # pylint: disable=W0212
  gitzip_exe = os.path.join(factory_commands._script_dir, 'gitzip.py')
  cmd = ['python', gitzip_exe,
         '--workdir', '.',
         '--url', '%schromium/src.git' % config.Master.git_server_url,
         '--gs_bucket', 'gs://chromium-git-bundles',
         '--gs_acl', 'public-read',
         '--timeout', '%d' % (60*60),
         '--stayalive', '200',
         '--verbose']
  factory.addStep(shell.ShellCommand, name='gitzip', description='gitzip',
                  timeout=7200, workdir='', command=cmd)

  builders = c.setdefault('builders', [])
  builders.append({
      'name': 'Chromium Git Packager',
      'builddir': 'chromium-git-packager',
      'factory': factory,
      'auto_reboot': False})

  schedulers = c.setdefault('schedulers', [])
  schedulers.append(Nightly(name='gitzip_nightly',
                            branch=None,
                            builderNames=['Chromium Git Packager'],
                            hour=2,
                            minute=40))
