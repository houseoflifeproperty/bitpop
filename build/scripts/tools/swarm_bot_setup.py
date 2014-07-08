#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup a given bot to become a swarm bot by installing the required files and
setting up any required scripts.

Assumes the bot already has python installed and a ssh server enabled.
"""

import optparse
import os
import subprocess
import sys


SWARM_DIRECTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'swarm_bootstrap')

# The directories to store the swarm code. Chromium-specific.
CHROMIUM_DEFAULT_SWARM_DIRECTORY = {
  'cygwin': '/cygdrive/e/b/swarm_slave',
  'linux': '/b/swarm_slave',
  'mac': '/b/swarm_slave',
  'win': 'e:\\b\\swarm_slave',
}


def CopySetupFiles(user, host, platform, dest_dir):
  """Copies the bootstrap files via sftp."""
  assert not dest_dir.endswith(('/', '\\'))

  if platform == 'win':
    # Skip the drive letter. The ftp server maps at c:\.
    dest_dir = dest_dir[2:].replace('\\', '/')
  sftp_stdin = ['rmdir %s' % dest_dir]

  directory = ''
  for path_section in dest_dir.lstrip('/').split('/'):
    directory = directory + '/' + path_section
    sftp_stdin.append('mkdir %s' % directory)

  sftp_stdin.extend(
      [
        'put swarm_bootstrap/* %s' % dest_dir,
        'exit',
      ])
  return ['sftp', user + '@' + host], '\n'.join(sftp_stdin)


def OpenSSHCommand(user, host):
  return ['ssh', '-o ConnectTimeout=5', '-t', user + '@' + host]


def BuildSetupCommand(user, host, platform, dest_dir, swarm_server):
  """Generates the command to run via ssh on the Swarm bot so it can setup
  itself.
  """
  assert platform in ('cygwin', 'linux', 'mac', 'win')
  bot_setup_commands = []

  # On Windows the swarm files need to be moved to the correct directory.
  # This is because sftp can't access drives other than c when copying the files
  # over.
  if platform == 'win':
    if dest_dir[0].lower() != 'c':
      # xcopy the file on the right drive.
      bot_setup_commands.extend([
          'xcopy /i /e /h /y %s %s\\' % ('c' + dest_dir[1:], dest_dir),
          '&&'])
    dest_dir += '\\'
  elif platform == 'cygwin':
    # A bit hackish but works.
    dest_dir = CHROMIUM_DEFAULT_SWARM_DIRECTORY['win'] + '\\'
  else:
    dest_dir += '/'

  # Download and setup the swarm code from the server.
  if platform == 'cygwin':
    # Hackish but for our deployment, depot_tools is always right aside.
    python = dest_dir + '..\\depot_tools\\python.bat'
  else:
    python = 'python'
  bot_setup_commands.extend(
      [python, dest_dir + 'swarm_bootstrap.py', '-s', swarm_server])

  # On windows the command must be executed by cmd.exe
  if platform in ('cygwin', 'win'):
    bot_setup_commands = ['cmd.exe /c',
                          '"' + ' '.join(bot_setup_commands) + '"']

  return OpenSSHCommand(user, host) + bot_setup_commands, ''


def BuildCleanCommand(user, host, platform, dest_dir):
  assert platform in ('cygwin', 'linux', 'mac', 'win')

  command = OpenSSHCommand(user, host)
  if platform == 'win':
    command.append('del /q /s %s' % dest_dir)
  else:
    command.append('rm -f -r %s' % dest_dir)

  return command, ''


def SendFilesToSwarmBotAndSelfSetup(bot, options):
  commands = []

  if options.clean:
    commands.append(
        BuildCleanCommand(options.user, bot, options.platform,
                          options.dest_dir))

  commands.append(
      CopySetupFiles(options.user, bot, options.platform, options.dest_dir))
  commands.append(
      BuildSetupCommand(options.user, bot, options.platform, options.dest_dir,
                        options.swarm_server))

  if options.print_only:
    for command, stdin in commands:
      print(' '.join(command))
      if stdin:
        print('\n'.join('  ' + l for l in stdin.splitlines()))
  else:
    for command, stdin in commands:
      print('Running: %s' % ' '.join(command))
      process = subprocess.Popen(command, stdin=subprocess.PIPE)
      process.communicate(stdin)
      print('')
      if process.returncode:
        print 'Failed to execute command %s' % command
        return 1
  return 0


def main():
  SWARM_SERVER_DEV = 'https://chromium-swarm-dev.appspot.com'
  parser = optparse.OptionParser(usage='%prog [options]',
                                 description=sys.modules[__name__].__doc__)
  parser.add_option('-b', '--bot', action='append', default=[], dest='bots',
                    help='Hostname(s) of bot(s) to setup as a swarm bot.')
  parser.add_option('-r', '--raw', metavar='FILE',
                    help='The name of a file containing line separated slaves '
                    'to setup. The slaves must all be the same os.')
  parser.add_option('-c', '--clean', action='store_true',
                    help='Removes any old swarm files before setting '
                    'up the bot.')
  parser.add_option('-d', '--use_dev', action='store_const',
                    help='Shorthand for --swarm_server %s; e.g. the '
                    'development swarm server instead of the production one.' %
                    SWARM_SERVER_DEV,
                    dest='swarm_server',
                    const=SWARM_SERVER_DEV)
  parser.add_option('--swarm_server', metavar='HOST',
                    help='Override the swarm master; default: %default',
                    default='https://chromium-swarm.appspot.com')
  parser.add_option('--dest_dir', metavar='DIR',
                    help='Override the swarm bot base dir')
  parser.add_option('-u', '--user', default='chrome-bot',
                    help='The user to use when setting up the machine. '
                    'default: %default')
  parser.add_option('-p', '--print_only', action='store_true',
                    help='Print what command would be executed to setup the '
                    'swarm bot.')
  parser.add_option('-w', '--win', action='store_const', dest='platform',
                    const='win')
  parser.add_option('-C', '--cygwin', action='store_const', dest='platform',
                    const='cygwin')
  parser.add_option('-l', '--linux', action='store_const', dest='platform',
                    const='linux')
  parser.add_option('-m', '--mac', action='store_const', dest='platform',
                    const='mac')


  options, args = parser.parse_args()

  if args:
    parser.error('Unknown arguments, %s' % args)
  if bool(options.bots) == bool(options.raw):
    parser.error('Must specify a bot or bot file.')
  if not options.platform:
    parser.error('Must specify the bot\'s OS.')

  if not options.dest_dir:
    options.dest_dir = CHROMIUM_DEFAULT_SWARM_DIRECTORY[options.platform]

  # Normalize the arguments.
  options.dest_dir = options.dest_dir.rstrip('/').rstrip('\\')
  options.swarm_server = options.swarm_server.rstrip('/')

  if options.raw:
    # Remove extra spaces and empty lines.
    options.bot.extend(
        filter(None, (s.strip() for s in open(options.raw, 'r'))))
  if not options.bots:
    parser.error('No bot to process.')

  for bot in options.bots:
    result = SendFilesToSwarmBotAndSelfSetup(bot, options)
    if result:
      return result
  return 0


if __name__ == '__main__':
  sys.exit(main())
