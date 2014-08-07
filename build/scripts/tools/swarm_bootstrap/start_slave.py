# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Returns a swarming bot dimensions and setups automatic startup if needed.

This file is uploaded the swarming server so the swarming bots can declare their
dimensions and startup method easily.
"""

import logging
import os
import socket
import sys

import os_utilities  # pylint: disable-msg=F0401
import zipped_archive  # pylint: disable-msg=F0401


def get_attributes():
  """Returns the attributes for this machine."""
  bot_id = socket.gethostname().lower().split('.', 1)[0]
  return os_utilities.get_attributes(bot_id)


def setup_bot():
  """Sets up the bot so it will survive an host restart.

  Returns True if it's fine to start the bot right away.
  """
  root_dir = os.getcwd()
  command = [
    sys.executable,
    os.path.abspath(zipped_archive.get_main_script_path()),
    'start_bot',
  ]
  if sys.platform == 'cygwin':
    # Replace the cygwin python command for the native one.
    # Find a depot_tools installation at a known location if it exists.
    for letter in ('c', 'e'):
      path = '/cygdrive/%s/b/depot_tools/python.bat' % letter
      if os.path.isfile(path):
        command[0] = path
        break
    else:
      logging.error('Unable to find python.bat')
      command[0] = 'python'

    os_utilities.setup_auto_startup_win(command, root_dir, 'run_swarm_bot.bat')
    # Because it was started in cygwin but we want only the bot to run on
    # native python, invariably force a reboot. #thisiswindows.
    return False

  elif sys.platform in 'win32':
    # Find a depot_tools installation at a known location if it exists.
    for letter in ('c', 'e'):
      path = letter + ':\\b\\depot_tools\\python.bat'
      if os.path.isfile(path):
        command[0] = path
        break
    else:
      logging.error('Unable to find python.bat')
      command[0] = 'python'

    os_utilities.setup_auto_startup_win(command, root_dir, 'run_swarm_bot.bat')
    # Invariably force a reboot. #thisiswindows.
    return False

  elif sys.platform == 'darwin':
    os_utilities.setup_auto_startup_osx(
        command, root_dir, 'org.swarm.bot.plist')
    # Restart so it is properly started by launchd. setup_bot() could be run via
    # ssh, which would break tests requiring UI.
    return False

  # No need to restart on Ubuntu since the bot is started via initd.
  return True
