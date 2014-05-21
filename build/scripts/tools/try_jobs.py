#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Cleans up the windows try slaves every night."""

from __future__ import with_statement
import os
import subprocess
import sys


def call(cmd, **kwargs):
  cmd = filter(None, cmd.split(' '))
  return subprocess.call(cmd, **kwargs)


def capture(cmd, **kwargs):
  cmd = filter(None, cmd.split(' '))
  print ' '.join(cmd)
  proc = subprocess.Popen(
      cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
  return proc.communicate()[0]


def run(base, jobs, subdir, extra_args):
  """Sends enough clobber try jobs to saturate a builders.

  Assumes the following directory hierarchy:
  build/
  chrome.git/src
  depot_tools/
  """
  subdir = subdir or 'chrome/src'
  os.chdir(os.path.join(base, subdir))
  old_branch = capture('git symbolic-ref HEAD').replace(
      'refs/heads/', '').strip()
  print "Old branch is %s" % old_branch
  # Hack to make sure git stash always works
  with open('LICENSE', 'a') as f:
    f.write('Foo\n')
  call('git stash -q')
  call('git checkout master -q')
  call('git branch -D try_job_cronjob_branch')
  call('git fetch origin -q')
  call('git checkout -b try_job_cronjob_branch origin/trunk -q')
  with open('LICENSE', 'a') as f:
    f.write('Foo\n')
  call('git commit -a -m . -q')
  call('svn up -q --non-interactive', cwd=os.path.join(base, 'build'))
  call('svn up -q --non-interactive', cwd=os.path.join(base, 'depot_tools'))

  def count_slaves(builder):
    return len(capture(
        os.path.join(base, 'build/scripts/tools/slaves.py') +
        ' -x t.c -w -l -m --builder ' +
        builder + ' -p').splitlines())

  def tryjob(builder, email):
    for i in range(count_slaves(builder)):
      cmd = (
          os.path.join(base, 'depot_tools/git-try') +
          ' --bot ' + builder +
          ' --name "cron_job_try' + str(i) + '" -c --email ' + email + ' ' +
          ' '.join(extra_args))
      #print cmd
      call(cmd)

  for builder, emails in jobs:
    tryjob(builder, emails)

  if old_branch == 'try_job_cronjob_branch':
    old_branch = 'master'
  call('git checkout ' + old_branch + ' -q')
  call('git stash pop -q')
  call('git checkout LICENSE -q')
  call('git branch -D try_job_cronjob_branch')
  return 0


def main():
  #emails1 = 'maruel@chromium.org'
  emails2 = 'maruel@chromium.org,phajdan.jr@chromium.org'
  #emails3 = 'maruel@chromium.org,timurrrr@chromium.org'

  jobs = [
      ('win', emails2),
      #('win_layout', emails1),
      #('mac', emails2),
      #('mac_layout', emails1),
      #('linux', emails2),
      #('linux_chromeos', emails1),
      #('linux_view', emails1),
      #('linux_layout', emails1),
      #('linux_valgrind', emails3),
      #('linux_chromeos_valgrind', emails3),
      #('linux_tsan', emails3),
  ]
  cur_dir = os.path.dirname(os.path.abspath(__file__))
  root_dir = os.path.realpath(os.path.join(cur_dir, '..', '..', '..'))
  if len(sys.argv) >= 2:
    subdir = sys.argv[1]
  else:
    subdir = None
  if len(sys.argv) > 2:
    extra_args = sys.argv[2:]
  else:
    extra_args = []
  print 'Using root dir %s' % root_dir
  return run(root_dir, jobs, subdir, extra_args)


if __name__ == '__main__':
  sys.exit(main())
