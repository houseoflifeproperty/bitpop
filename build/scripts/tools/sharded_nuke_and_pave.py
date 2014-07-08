#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Issues sharded slavekill, delete build directory, and reboot commands."""

import multiprocessing
import optparse
import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common import chromium_utils
from master import slaves_list


def get_masters(parser, options):
  """Given parser options, find suitable master directories."""
  paths = []
  masters_path = chromium_utils.ListMasters()

  # Populates by defaults with every masters with a twistd.pid, thus has
  # been started.
  if not options.master:
    for m_p in masters_path:
      if  os.path.isfile(os.path.join(m_p, 'twistd.pid')):
        paths.append(m_p)
  elif options.master == 'all':
    paths.extend(masters_path)
  elif options.master in (os.path.basename(p) for p in masters_path):
    full_master = next(
        p for p in masters_path if os.path.basename(p) == options.master)
    paths.append(full_master)
  else:
    parser.error('Unknown master \'%s\'.\nChoices are:\n  %s' % (
        options.master, '\n  '.join((
            os.path.basename(p) for p in masters_path))))
  return paths


def get_slaves(master_paths, slavelist):
  """Return slaves split up by OS.

  Takes a list of master paths and an optional slave whitelist."""

  slavedict = {}
  for path in master_paths:
    for slave in chromium_utils.RunSlavesCfg(os.path.join(path, 'slaves.cfg')):
      if 'hostname' in slave:
        slavedict[slave['hostname']] = slave
  slaves = slaves_list.BaseSlavesList(slavedict.values())
  def F(os_type):
    out = slaves.GetSlaves(os=os_type)
    named_slaves = [s.get('hostname') for s in out]

    if slavelist:
      return [s for s in named_slaves if s in slavelist]
    else:
      return named_slaves

  slave_dict = {}
  slave_dict['win'] = list(set(F('win')))
  slave_dict['linux'] = list(set(F('linux')))
  slave_dict['mac'] = list(set(F('mac')))

  return slave_dict


def get_commands(slaves):
  """Depending on OS, yield the proper nuke-and-pave command sequence."""
  commands = {}
  for slave in slaves['win']:
    def cmd(command):
      return 'cmd.exe /c "%s"' % command
    def cygwin(command):
      return 'c:\\cygwin\\bin\\bash --login -c "%s"' % (
          command.replace('"', '\\"'))

    commands[slave] = [
        cmd('taskkill /IM python.exe /F'),
        cygwin('sleep 3'),
        cygwin('rm -r -f /cygdrive/e/b/build/slave/*/build'),
        cmd('shutdown -r -f -t 1'),
    ]

  for slave in slaves['mac'] + slaves['linux']:
    commands[slave] = [
        'make -C /b/build/slave stop',
        'sleep 3',
        'rm -rf /b/build/slave/*/build',
        'sudo shutdown -r now',
    ]
  return commands


def status_writer(queue):
  # Send None to kill the status writer.
  msg = queue.get()
  while msg:
    print '\n'.join(msg)
    msg = queue.get()


def stdout_writer(queue):
  # Send None to kill the stdout writer.
  slave = queue.get()
  while slave:
    print '%s: finished' % slave
    slave = queue.get()


def journal_writer(filename, queue):
  # Send None to kill the journal writer.
  with open(filename, 'a') as f:
    slave = queue.get()
    while slave:
      # pylint: disable=C0323
      print >>f, slave
      slave = queue.get()


def shard_slaves(slaves, max_per_shard):
  """Shart slaves with no more than max_per_shard in each shard."""
  shards = []
  for i in xrange(0, len(slaves), max_per_shard):
    shards.append(list(slaves.iteritems())[i:i+max_per_shard])
  return shards


def run_ssh_command(slavepair, worklog, status,  errorlog, options):
  """Execute an ssh command as chrome-bot."""
  slave, commands = slavepair
  needs_connect = slave.endswith('-c4')
  if options.corp:
    slave = slave + '.chrome'

  if needs_connect:
    ssh = ['connect', slave, '-r']
  else:
    identity = ['chrome-bot@%s' % slave]
    ssh = ['ssh', '-o ConnectTimeout=5'] + identity
  if options.dry_run:
    for command in commands:
      status.put(['%s: %s' % (slave, command)])
    return

  retcode = 0
  for command in commands:
    status.put(['%s: %s' % (slave, command)])
    retcode = subprocess.call(ssh + [command])
    if options.verbose:
      status.put(['%s: previous command returned code %d' % (slave, retcode)])
    if retcode != 0 and command != commands[0]:  # Don't fail on slavekill.
      break

  if retcode == 0:
    worklog.put(slave)
  else:
    errorlog.put(slave)


class Worker(object):
  def __init__(self, out_queue, status, errorlog, options):
    self.out_queue = out_queue
    self.status = status
    self.options = options
    self.errorlog = errorlog
  def __call__(self, slave):
    run_ssh_command(slave, self.out_queue, self.status, self.errorlog,
                    self.options)


def main():
  usage = '%prog [options]'
  parser = optparse.OptionParser(usage=usage)
  parser.add_option('--master',
      help=('Master to use to load the slaves list. If omitted, all masters '
            'that were started at least once are included. If \'all\', all '
            'masters are selected.'))
  parser.add_option('--slavelist',
      help=('List of slaves to contact, separated by newlines.'))
  parser.add_option('--max-per-shard', default=50,
      help=('Each shard has no more than max-per-shard slaves.'))
  parser.add_option('--max-connections', default=16,
      help=('Maximum concurrent SSH sessions.'))
  parser.add_option('--journal',
      help=('Log completed slaves to a journal file, skipping them'
            'on the next run.'))
  parser.add_option('--errorlog',
      help='Log failed slaves to a file instead out stdout.')
  parser.add_option('--dry-run', action='store_true',
      help='Don\'t execute commands, only print them.')
  parser.add_option('--corp', action='store_true',
      help='Connect to bots within the corp network.')
  parser.add_option('-v', '--verbose', action='store_true')
  options, _ = parser.parse_args(sys.argv)

  masters = get_masters(parser, options)
  if options.verbose:
    print 'reading from:'
    for master in masters:
      print '  ', master

  slavelist = []
  if options.slavelist:
    with open(options.slavelist) as f:
      slavelist = [s.strip() for s in f.readlines()]
  slaves = get_slaves(masters, slavelist)

  if options.verbose and options.slavelist:
    wanted_slaves = set(slavelist)
    got_slaves = set()
    for _, s in slaves.iteritems():
      got_slaves.update(s)

    diff = wanted_slaves - got_slaves
    if diff:
      print 'Following slaves are not on selected masters:'
      for s in diff:
        print '  ', s

  if options.journal and os.path.exists(options.journal):
    skipped = set()
    with open(options.journal) as f:
      finished_slaves = set([s.strip() for s in f.readlines()])
    for os_type in slaves:
      skipped.update(set(slaves[os_type]) & finished_slaves)
      slaves[os_type] = list(set(slaves[os_type]) - finished_slaves)
    if options.verbose:
      print 'Following slaves have already been processed:'
      for s in skipped:
        print '  ', s

  commands = get_commands(slaves)
  shards = shard_slaves(commands, options.max_per_shard)
  pool = multiprocessing.Pool(processes=options.max_connections)
  m = multiprocessing.Manager()
  worklog = m.Queue()
  status = m.Queue()
  errors = m.Queue()

  # Set up the worklog and status writers.
  if options.journal:
    p = multiprocessing.Process(target=journal_writer,
                                args=(options.journal, worklog))
  else:
    p = multiprocessing.Process(target=stdout_writer, args=(worklog,))
  s = multiprocessing.Process(target=status_writer, args=(status,))

  p.start()
  s.start()

  # Execute commands.
  for shard in shards:
    if options.verbose:
      print 'Starting next shard with slaves:'
      for slave in shard:
        print '  ', slave

    pool.map_async(Worker(worklog, status, errors, options), shard).get(9999999)
    raw_input('Shard finished, press enter to continue...')

  # Clean up the worklog and status writers.
  worklog.put(None)  # Signal worklog writer to stop.
  status.put(None)  # Signal status writer to stop.
  p.join()
  s.join()

  # Print out errors.
  error_list = []
  errors.put(None)  # Signal end of error list.
  e = errors.get()
  while e:
    error_list.append(e)
    e = errors.get()
  if error_list:
    if options.errorlog:
      with open(options.errorlog, 'w') as f:
        for error in error_list:
          # pylint: disable=C0323
          print >>f, error
    else:
      print 'Following slaves had errors:'
      for error in error_list:
        print '  ', error

  return 0


if __name__ == '__main__':
  sys.exit(main())
