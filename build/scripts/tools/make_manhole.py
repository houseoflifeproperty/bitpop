#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generate a .manhole for all masters."""

import getpass
import os
import optparse
import subprocess
import sys


def check_output(cmd):
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  stdout = p.communicate(None)[0]
  if p.returncode:
    raise subprocess.CalledProcessError(p.returncode, cmd)
  return stdout


def main():
  parser = optparse.OptionParser()
  parser.add_option('-u', '--user', default=getpass.getuser())
  parser.add_option('-p', '--port', type='int', help='Base port')
  parser.add_option('-r', '--root', default=os.getcwd(), help='Path to masters')
  options, args = parser.parse_args(None)

  if args:
    parser.error('Have you tried not using the wrong argument?')
  if not options.port:
    parser.error('Use --port to specify a base port')
  if not os.path.basename(options.root) == 'masters':
    parser.error('Use --root or cd into the masters directory')

  try:
    check_output(['apg', '-q', '-n', '1'])
  except subprocess.CalledProcessError:
    parser.error('Run sudo apt-get install apg')

  for i in os.listdir(options.root):
    if i.startswith('.'):
      continue
    dirpath = os.path.join(options.root, i)
    if not os.path.isdir(dirpath):
      continue
    if not os.path.isfile(os.path.join(dirpath, 'buildbot.tac')):
      print '%-30s has no buildbot config' % i
      continue
    filepath = os.path.join(dirpath, '.manhole')
    if os.path.isfile(filepath):
      print '%-30s already had .manhole' % i
      continue
    print '%-30s Generating password' % i
    password = check_output(['apg', '-q', '-n', '1']).strip()
    content = "user='%s'\npassword='/!%s'\nport=%d\n" % (
      options.user, password, options.port)
    options.port += 1
    open(filepath, 'w').write(content)
  return 0


if __name__ == '__main__':
  sys.exit(main())
