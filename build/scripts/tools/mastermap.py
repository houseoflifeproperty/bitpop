#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tool for viewing masters, their hosts and their ports.

Has two main modes:
  a) In normal mode, simply prints the list of all known masters, sorted by
     hostname, along with their associated ports, for the perusal of the user.
  b) In --audit mode, tests to make sure that no masters conflict/overlap on
     ports (even on different masters) and that no masters have unexpected
     ports (i.e. differences of more than 100 between master, slave, and alt).
     Audit mode returns non-zero error code if conflicts are found. In audit
     mode, --verbose causes it to print human-readable output as well.

In both modes, --csv causes the output (if any) to be formatted as
comma-separated values.
"""

import optparse
import os
import sys

# Should be <snip>/build/scripts/tools
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'site_config'))

import config_bootstrap
from slave import bootstrap

# These are ports likely to be running on a developer's machine, which may break
# presubmit tests.
PORT_BLACKLIST = set([
    8000,  # SimpleHTTPServer, dev_appserver.py
    8080,  # dev_appserver.py
    8088,  # goma
    8103,  # sshd
    8224,  # google-specific
])

def get_args():
  """Process command-line arguments."""
  parser = optparse.OptionParser(
      description='Tool to list all masters along with their hosts and ports.')

  parser.add_option('-l', '--list', action='store_true', default=False,
                    help='Output a list of all ports in use by all masters. '
                         'Default behavior if no other options are given.')
  parser.add_option('--sort-by', action='store',
                    help='Define the primary key by which rows are sorted. '
                    'Possible values are: "port", "alt_port", "slave_port", '
                    '"host", and "name". Only one value is allowed (for now).')
  parser.add_option('--find', action='store', type='int', default=0,
                    metavar='N',
                    help='Output N sets of three available ports.')
  parser.add_option('--audit', action='store_true', default=False,
                    help='Output conflict diagnostics and return an error '
                         'code if misconfigurations are found.')
  parser.add_option('--presubmit', action='store_true', default=False,
                    help='The same as --audit, but prints no output. '
                         'Overrides all other options.')

  parser.add_option('--csv', action='store_true', default=False,
                    help='Print output in comma-separated values format.')

  opts, _ = parser.parse_args()

  opts.verbose = True

  if not (opts.find or opts.audit or opts.presubmit):
    opts.list = True

  if opts.presubmit:
    opts.list = False
    opts.audit = True
    opts.find = False
    opts.verbose = False

  return opts


def getint(string):
  """Try to parse an int (port number) from a string."""
  try:
    ret = int(string)
  except ValueError:
    ret = 0
  return ret


def human_print(lines, verbose):
  """Given a list of lists of tokens, pretty prints them in columns.

  Requires all lines to have the same number of tokens, as otherwise the desired
  behavior is not clearly defined (i.e. which columns should be left empty for
  shorter lines?).
  """

  for line in lines:
    assert len(line) == len(lines[0])

  num_cols = len(lines[0])
  format_string = ''
  for col in xrange(num_cols - 1):
    col_width = max(len(str(line[col])) for line in lines) + 1
    format_string += '%-' + str(col_width) + 's '
  format_string += '%s'

  if verbose:
    for line in lines:
      print(format_string % tuple(line))
    print('\n')


def csv_print(lines, verbose):
  """Given a list of lists of tokens, prints them as comma-separated values.

  Requires all lines to have the same number of tokens, as otherwise the desired
  behavior is not clearly defined (i.e. which columns should be left empty for
  shorter lines?).
  """

  for line in lines:
    assert len(line) == len(lines[0])

  if verbose:
    for line in lines:
      print(','.join(str(t) for t in line))
    print('\n')


def master_map(masters, output, opts):
  """Display a list of masters and their associated hosts and ports."""

  lines = [['Master', 'Config Dir', 'Host', 'Web port', 'Slave port',
            'Alt port', 'MSC', 'URL']]
  for master in masters:
    lines.append([
        master['name'], master['dirname'], master['host'], master['port'],
        master['slave_port'], master['alt_port'], master['msc'],
        master['buildbot_url']])

  output(lines, opts.verbose)


def master_audit(masters, output, opts):
  """Check for port conflicts and misconfigurations on masters.

  Outputs lists of masters whose ports conflict and who have misconfigured
  ports. If any misconfigurations are found, returns a non-zero error code.
  """
  # Return value. Will be set to 1 the first time we see an error.
  ret = 0

  # Look for masters configured to use the same ports.
  web_ports = {}
  slave_ports = {}
  alt_ports = {}
  all_ports = {}
  for master in masters:
    web_ports.setdefault(master['port'], []).append(master)
    slave_ports.setdefault(master['slave_port'], []).append(master)
    alt_ports.setdefault(master['alt_port'], []).append(master)

    for port_type in ('port', 'slave_port', 'alt_port'):
      all_ports.setdefault(master[port_type], []).append(master)

  # Check for blacklisted ports.
  lines = [['Blacklisted port', 'Master', 'Host']]
  for port, lst in all_ports.iteritems():
    if port in PORT_BLACKLIST:
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Check for conflicting web ports.
  lines = [['Web port', 'Master', 'Host']]
  for port, lst in web_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Check for conflicting slave ports.
  lines = [['Slave port', 'Master', 'Host']]
  for port, lst in slave_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Check for conflicting alt ports.
  lines = [['Alt port', 'Master', 'Host']]
  for port, lst in alt_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Look for masters whose port, slave_port, alt_port aren't separated by 100.
  lines = [['Master', 'Host', 'Web port', 'Slave port', 'Alt port']]
  for master in masters:
    if (getint(master['slave_port']) - getint(master['port']) != 100 or
        getint(master['alt_port']) - getint(master['slave_port']) != 100):
      ret = 1
      lines.append([master['name'], master['host'],
                   master['port'], master['slave_port'], master['alt_port']])
  output(lines, opts.verbose)

  return ret


def find_port(masters, output, opts):
  """Lists triplets of available ports for easy discoverability."""
  ports = set()
  for master in masters:
    for port in ('port', 'slave_port', 'alt_port'):
      ports.add(master[port])

  # Remove 0 from the set.
  ports = ports - {0}

  # Add blacklisted ports.
  ports = ports | PORT_BLACKLIST

  lines = [['Web port', 'Slave port', 'Alt port']]
  # In case we've hit saturation, search one past the end of the port list.
  for port in xrange(min(ports), max(ports) + 2):
    if (port not in ports and
        port + 100 not in ports and
        port + 200 not in ports):
      lines.append([port, port + 100, port + 200])
      if len(lines) > opts.find:
        break

  output(lines, opts.verbose)


def extract_masters(masters):
  """Extracts the data we want from a collection of possibly-masters."""
  good_masters = []
  for master_name, master in masters.iteritems():
    if not hasattr(master, 'master_port'):
      # Not actually a master
      continue
    host = getattr(master, 'master_host', '')
    for suffix in ('.chromium.org', '.corp.google.com'):
      if host.endswith(suffix):
        host = host[:-len(suffix)]
        break
    good_masters.append({
        'name': master_name,
        'host': host,
        'port': getattr(master, 'master_port', 0),
        'slave_port': getattr(master, 'slave_port', 0),
        'alt_port': getattr(master, 'master_port_alt', 0),
        'buildbot_url': getattr(master, 'buildbot_url', ''),
        'dirname': os.path.basename(getattr(master, 'local_config_path', ''))
    })
  return good_masters


def real_main(include_internal=False):
  opts = get_args()

  bootstrap.ImportMasterConfigs(include_internal=include_internal)

  # These are the masters that are configured in site_config/.
  config_masters = extract_masters(
      config_bootstrap.config_private.Master.__dict__)
  for master in config_masters:
    master['msc'] = ''

  # These are the masters that have their own master_site_config.
  msc_masters = extract_masters(config_bootstrap.Master.__dict__)
  for master in msc_masters:
    master['msc'] = 'Y'

  # Define sorting order
  sort_keys = ['port', 'alt_port', 'slave_port', 'host', 'name']
  # Move key specified on command-line to the front of the list
  if opts.sort_by is not None:
    try:
      index = sort_keys.index(opts.sort_by)
    except ValueError:
      pass
    else:
      sort_keys.insert(0, sort_keys.pop(index))

  sorted_masters = config_masters + msc_masters
  for key in reversed(sort_keys):
    sorted_masters.sort(key = lambda m: m[key])

  if opts.csv:
    printer = csv_print
  else:
    printer = human_print

  if opts.list:
    master_map(sorted_masters, printer, opts)

  ret = 0
  if opts.audit or opts.presubmit:
    ret = master_audit(sorted_masters, printer, opts)

  if opts.find:
    find_port(sorted_masters, printer, opts)

  return ret


def main():
  return real_main(include_internal=False)


if __name__ == '__main__':
  sys.exit(main())
