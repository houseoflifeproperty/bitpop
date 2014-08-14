#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Sets up the swarming slave to connect to the swarm server.

This file is uploaded the swarming server so the swarming slaves can update
their dimensions and startup method easily.
"""

import json
import logging
import logging.handlers
import optparse
import os
import platform
import socket
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# A mapping between sys.platform values and the corresponding swarm name
# for that platform.
PLATFORM_MAPPING = {
  'cygwin': 'Windows',
  'darwin': 'Mac',
  'linux2': 'Linux',
  'win32': 'Windows',
}


def WriteToFile(filepath, content):
  """Writes out a file.

  Returns True on success.
  """
  logging.debug('Writing new file, %s, with contents:\n%s', filepath,
                content)
  try:
    with open(filepath, mode='w') as f:
      f.write(content)
    return True
  except IOError as e:
    logging.error('Cannot write file %s: %s', filepath, e)
    return False


def WriteJsonToFile(filepath, data):
  """Writes out a json file.

  Returns True on success.
  """
  return WriteToFile(filepath, json.dumps(data, sort_keys=True, indent=2))


def ConvertMacVersion(version):
  """Returns the major OSX version, like 10.7, 10.8, etc."""
  version_parts = version.split('.')

  assert len(version_parts) >= 2, 'Unable to determine Mac version'
  return '.'.join(version_parts[:2])


def ConvertWindowsVersion(version):
  """Returns the major Windows version, like 5.0, 5.1, 6.2, etc."""
  if '-' in version:
    version = version.split('-')[1]

  version_parts = version.split('.')
  assert len(version_parts) >= 2,  'Unable to determine Windows version'

  return '.'.join(version_parts[:2])


def GetPlatformVersion():
  if sys.platform == 'cygwin':
    return ConvertWindowsVersion(platform.system())

  elif sys.platform == 'win32':
    return ConvertWindowsVersion(platform.version())

  elif sys.platform == 'darwin':
    return ConvertMacVersion(platform.mac_ver()[0])

  elif sys.platform == 'linux2':
    # No need to convert the linux value since it already returns what we
    # want (like '12.04' or '10.04' for ubuntu slaves).
    return platform.linux_distribution()[1]

  raise Exception('Unable to determine platform version')


def GetMachineType():
  """Returns the type of processor. Should be ARM, x86 or x64."""
  machine = platform.machine()
  if machine in ('AMD64', 'x86_64'):
    # Normalize the value returned on Windows (AMD64) and other platforms
    # (x86_64).
    return 'x64'
  if machine == 'i386':
    return 'x86'
  return machine


def GetArchitectureSize():
  """Returns the number of bits in the systems architecture."""
  machine = GetMachineType()
  if machine == 'x64':
    return '64'
  if machine == 'x86':
    return '32'
  # Fallback.
  return '64' if sys.maxsize > 2**32 else '32'


def GetDimensions(hostname, platform_id, platform_version):
  """Returns a dictionary of attributes representing this machine.

  Returns:
    A dictionary of the attributes of the machine.
  """
  if platform_id not in PLATFORM_MAPPING:
    logging.error('Running on an unknown platform, %s, unable to '
                  'generate dimensions', platform_id)
    return {}

  platform_name = PLATFORM_MAPPING[platform_id]

  return {
    'dimensions': {
      'bits': GetArchitectureSize(),
      'hostname': hostname,
      'machine': GetMachineType(),
      'os': [
          platform_name,
          platform_name + '-' + platform_version,
      ],
    },
    'tag': hostname,
  }


def GetChromiumDimensions(hostname, platform_id, platform_version):
  """Returns chromium infrastructure specific dimensions."""
  dimensions = GetDimensions(hostname, platform_id, platform_version)
  if not dimensions:
    return dimensions

  hostname = dimensions['tag']
  # Get the vlan of this machine from the hostname when it's in the form
  # '<host>-<vlan>'.
  if '-' in hostname:
    dimensions['dimensions']['vlan'] = hostname.split('-')[-1]
    # Replace vlan starting with 'c' to 'm'.
    if dimensions['dimensions']['vlan'][0] == 'c':
      dimensions['dimensions']['vlan'] = (
          'm' + dimensions['dimensions']['vlan'][1:])
  return dimensions


def GenerateAndWriteDimensions(dimensions_file):
  """Generates and stores the dimensions for this machine.

  Args:
    dimensions_file: The location to write the dimension file to.

  Returns:
    0 if the dimension file is successfully generated, 1 otherwise.
  """
  logging.info('Generating and writing dimensions to %s', dimensions_file)

  hostname = socket.gethostname().lower().split('.', 1)[0]
  dimensions = GetChromiumDimensions(hostname, sys.platform,
                                     GetPlatformVersion())

  if not WriteJsonToFile(dimensions_file, dimensions):
    return 1

  return 0


def ConvertCygwinPath(path):
  """Convert a full cygwin path to a standard Windows path."""
  if not path.startswith('/cygdrive/'):
    logging.warning('%s is not a cygwin path', path)
    return None

  # Remove the cygwin path identifier.
  path = path.replace('/cygdrive/', '')

  # Add : after the drive letter.
  path = path[:1] + ':' + path[1:]

  return path.replace('/', '\\')


def SetupAutoStartupWin(command):
  """Uses Startup folder in the Start Menu.

  Works both inside cygwin's python or native python.
  """
  # TODO(maruel): Not always true. Read from registry if needed.
  print('OS version is: %s' % GetPlatformVersion())
  if GetPlatformVersion() == '5.1':
    startup = 'Start Menu\\Programs\\Startup'
  else:
    # Vista+
    startup = (
        'AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup')

  # On cygwin 1.5, which is still used on some slaves, '~' points inside
  # c:\\cygwin\\home.
  path = '%s\\%s\\run_swarm_bot.bat' % (
      os.environ.get('USERPROFILE', 'DUMMY, ONLY USED IN TESTS'), startup)
  swarm_directory = BASE_DIR

  # If we are running through cygwin, the path to write to must be changed to be
  # in the cywgin format, but we also need to change the commands to be in
  # non-cygwin format (since they will execute in a batch file).
  if sys.platform == 'cygwin':
    path = path.replace('\\', '/')

    swarm_directory = ConvertCygwinPath(swarm_directory)

    # Convert all the cygwin paths in the command.
    for i in range(len(command)):
      if '/cygdrive/' in command[i]:
        command[i] = ConvertCygwinPath(command[i])

    # Replace the python command.
    # TODO(csharp): This should just be 'python'.
    c_drive_python = '/cygdrive/c/b/depot_tools/python.bat'
    e_drive_python = '/cygdrive/e/b/depot_tools/python.bat'
    if os.path.exists(c_drive_python):
      command[0] = ConvertCygwinPath(c_drive_python)
    elif os.path.exists(e_drive_python):
      command[0] = ConvertCygwinPath(e_drive_python)
    else:
      raise Exception('Unable to find python.bat')

  content = '@cd /d ' + swarm_directory + ' && ' + ' '.join(command)
  return WriteToFile(path, content)


def GenerateLaunchdPlist(command):
  """Generates a plist with the corresponding command."""
  # The documentation is available at:
  # https://developer.apple.com/library/mac/documentation/Darwin/Reference/ \
  #    ManPages/man5/launchd.plist.5.html
  entries = [
    '<key>Label</key><string>org.swarm.bot</string>',
    '<key>StandardOutPath</key><string>swarm_bot.log</string>',
    '<key>StandardErrorPath</key><string>swarm_bot-err.log</string>',
    '<key>LimitLoadToSessionType</key><array><string>Aqua</string></array>',
    '<key>RunAtLoad</key><true/>',
    '<key>Umask</key><integer>18</integer>',

    '<key>EnvironmentVariables</key>',
    '<dict>',
    '  <key>PATH</key>',
    '  <string>/opt/local/bin:/opt/local/sbin:/usr/local/sbin:/usr/local/bin'
      ':/usr/sbin:/usr/bin:/sbin:/bin</string>',
    '</dict>',

    '<key>SoftResourceLimits</key>',
    '<dict>',
    '  <key>NumberOfFiles</key>',
    '  <integer>8000</integer>',
    '</dict>',
  ]
  entries.append('<key>Program</key><string>%s</string>' % command[0])
  entries.append('<key>ProgramArguments</key>')
  entries.append('<array>')
  # Command[0] must be passed as an argument.
  entries.extend('  <string>%s</string>' % i for i in command)
  entries.append('</array>')
  entries.append('<key>WorkingDirectory</key><string>%s</string>' % BASE_DIR)
  header = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
    '<plist version="1.0">\n'
    '  <dict>\n'
    + ''.join('    %s\n' % l for l in entries) +
    '  </dict>\n'
    '</plist>\n')
  return header


def SetupAutoStartupOSX(command):
  """Uses launchd with auto-login user."""
  plistname = os.path.expanduser('~/Library/LaunchAgents/org.swarm.bot.plist')
  return WriteToFile(plistname, GenerateLaunchdPlist(command))


def SetupAutoStartup(slave_machine, swarm_server, server_port, dimensionsfile):
  logging.info('Generating AutoStartup')

  command = [
    sys.executable,
    slave_machine,
    '-a', swarm_server,
    '-p', server_port,
    '-r', '400',
    '--keep_alive',
    '-v',
    dimensionsfile,
  ]
  if sys.platform in ('cygwin', 'win32'):
    return SetupAutoStartupWin(command)
  elif sys.platform == 'darwin':
    return SetupAutoStartupOSX(command)
  else:
    logging.info('Skipping Autostart for Linux since they should have an up to '
                 'conf file that handles their startup')


def main():
  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option('-s', '--swarm-server')
  parser.add_option('-p', '--port')
  options, _args = parser.parse_args()

  # Setup up logging to a constant file.
  logging_rotating_file = logging.handlers.RotatingFileHandler(
      'start_slave.log',
      maxBytes=2 * 1024 * 1024, backupCount=2)
  logging_rotating_file.setLevel(logging.DEBUG)
  logging_rotating_file.setFormatter(logging.Formatter(
      '%(asctime)s %(levelname)-8s %(module)15s(%(lineno)4d): %(message)s'))
  logging.getLogger('').addHandler(logging_rotating_file)
  logging.getLogger('').setLevel(logging.DEBUG)

  if options.swarm_server and options.port:
    dimensions_file = os.path.join(BASE_DIR, 'dimensions.in')

    # Only reset the dimensions if the server is given, because the auto
    # startup code needs to also be run to ensure the slave is reading the
    # correct dimensions file.
    GenerateAndWriteDimensions(dimensions_file)

    slave_machine = os.path.join(BASE_DIR, 'slave_machine.py')

    SetupAutoStartup(slave_machine, options.swarm_server, options.port,
                     dimensions_file)

  logging.debug('Restarting machine')
  import slave_machine  # pylint: disable-msg=F0401
  slave_machine.Restart()


if __name__ == '__main__':
  try:
    sys.exit(main())
  except Exception as e:
    logging.exception(e)
    sys.exit(1)
