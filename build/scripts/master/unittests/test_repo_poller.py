#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import subprocess
import tempfile

import twisted
from twisted.application import service
from twisted.internet import defer, task, reactor
from twisted.mail import smtp
from twisted.trial import unittest
import buildbot.changes.base

class MasterProxy(object):
  def __init__(self):
    self.changes = []
  def addChange(self, *args, **kwargs):
    self.changes.append((args, kwargs))
    return defer.succeed(0)

class PollingChangeSourceProxy(service.Service):
  def __init__(self):
    self.master = None
  def startService(self):
    self.master = MasterProxy()
    service.Service.startService(self)
  def stopService(self):
    return service.Service.stopService(self)

SENT_MAILS = []

def sendmail_proxy(smtphost, from_addr, to_addrs, msg,
                   senderDomainName=None, port=25):
  SENT_MAILS.append((smtphost, from_addr, to_addrs, msg,
                     senderDomainName, port))
  return defer.succeed(0)

buildbot.changes.base.PollingChangeSource = PollingChangeSourceProxy
smtp.sendmail = sendmail_proxy

from master.repo_poller import RepoPoller

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'repo'))
REPO_BIN = os.path.join(REPO_DIR, 'repo')
REPO_URL = os.path.join(REPO_DIR, 'clone.bundle')

REPO_BRANCHES = ['master', 'foo_branch', 'bar_branch']

REPO_MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <remote  name="default" fetch="." />
  <default revision="%(branch)s" remote="default" sync-j="1" />
  <project name="git0" />
  <project name="git1" />
  <project name="git2" />
  <project name="%(branch-unique-project)s" />
</manifest>
"""

# 3 projects present in all manifest branches + 1 unique to each branch
PROJ_COUNT = 3 + 1

BRANCH_UNIQUE_PROJ_NAME = '%s-unique_porject'

# In the setup code, we create all REPO_BRANCHES by adding a new commit on top
# of the one before, which yields a commit graph such that
# REPO_BRANCHES[0] <- REPO_BRANCHES[1] <- REPO_BRANCHES[2] ... where "<-" means
# "is parent of". This results in "git log" listing n+1 commits for
# REPO_BRANCHES[n], and since we have the same graph for each constituent
# project, we end up picking up initially, at least these many revs
# TODO(gjorge) check with szager if this use of the RepoTagComparator makes
# sense at all under this new "multi-branch" scenario
INITIAL_REVS_DETECTED = PROJ_COUNT * sum(range(1, len(REPO_BRANCHES)+1))

class TestRepoPoller(unittest.TestCase):

  def setUp(self):
    self.workdir = tempfile.mkdtemp(prefix='repo_poller_simple_test')
    self.repo_src = os.path.join(self.workdir, 'repo-src')
    self.repo_work = os.path.join(self.workdir, 'repo-work')

    manifest_dir = os.path.join(self.repo_src, 'manifest')
    git_dir_base = os.path.join(self.repo_src, 'git')
    git_dirs = ['%s%d' % (git_dir_base, x) for x in range(PROJ_COUNT)]
    git_dirs += [os.path.join(self.repo_src, BRANCH_UNIQUE_PROJ_NAME % br)
                 for br in REPO_BRANCHES]

    for d in git_dirs + [manifest_dir, self.repo_work]:
      if not os.path.exists(d):
        os.makedirs(d)

    for d in git_dirs + [manifest_dir]:
      self.assertFalse(_cmd(['git', 'init', '--quiet'], d))

    def _masterToFront(x, y): return int(y == 'master') - int(x == 'master')
    REPO_BRANCHES.sort(cmp=_masterToFront)

    for n, branch in enumerate(REPO_BRANCHES):
      # when n==0 we're creating master, and 'checkout -b' will fail
      self.assertFalse(_cmd(['git', 'checkout', '-q', '-b', branch],
                            manifest_dir)
                       and n!=0)
      fh = open(os.path.join(manifest_dir, 'default.xml'), 'w')
      fh.write(REPO_MANIFEST %
               {'branch': branch,
                'branch-unique-project': BRANCH_UNIQUE_PROJ_NAME % branch})
      fh.close()
      self.assertFalse(_cmd(['git', 'add', 'default.xml'], manifest_dir))
      self.assertFalse(_cmd(['git', 'commit', '-q', '-m', 'empty'],
                            manifest_dir))
    # repo does something too smart with the commiter's email while switching
    # branches within the manifest project that confuses it. We need to change
    # it here before we try using the project from a repo client, else
    # `repo init` fails
    self.assertFalse(_cmd(['git', 'filter-branch', '-f', '--env-filter',
                           'GIT_COMMITTER_EMAIL=no_one'] + REPO_BRANCHES,
                          manifest_dir))

    for n, branch in enumerate(REPO_BRANCHES):
      for x, git_dir in enumerate(git_dirs):
        # when n==0 we're creating master, and 'checkout -b' will fail
        self.assertFalse(_cmd(['git', 'checkout', '-q', '-b', branch], git_dir)
                         and n!=0)
        fh = open(os.path.join(git_dir, 'file%d.txt' % x), 'w')
        fh.write('Contents of file%d.txt in branch %s\n' % (x, branch))
        fh.close()
        self.assertFalse(_cmd(['git', 'add', 'file%d.txt' % x], git_dir))
        self.assertFalse(_cmd(['git', 'commit', '-q', '-m', 'empty'], git_dir))


    cmd = [REPO_BIN, 'init', '--no-repo-verify',
           '--repo-url', REPO_URL, '-u', manifest_dir]
    self.assertFalse(_cmd(cmd, self.repo_work))
    self.poller = RepoPoller(self.repo_src, repo_branches=REPO_BRANCHES,
                             workdir=self.repo_work, pollInterval=999999,
                             repo_bin=REPO_BIN, from_addr='sender@example.com',
                             to_addrs='recipient@example.com',
                             smtp_host='nohost')
    self.poller.startService()

  def tearDown(self):
    self.poller.stopService()
    shutil.rmtree(self.workdir)

  def _modifySrcFile(self, gitname, filename, comment='comment',
                     branch='master'):
    src_dir = os.path.join(self.repo_src, gitname)
    self.assertFalse(_cmd(['git', 'checkout', branch], src_dir))
    src_file = os.path.join(src_dir, filename)
    fh = open(src_file, 'a')
    fh.write('A change to %s.' % filename)
    fh.close()
    self.assertFalse(_cmd(['git', 'add', filename], src_dir))
    self.assertFalse(_cmd(['git', 'commit', '-q', '-m', comment], src_dir))

  @defer.deferredGenerator
  def test1_simple(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()
    self.assertEqual(
        len(self.poller.comparator.tag_order), INITIAL_REVS_DETECTED,
        "%d initial revisions in repo checkout." % INITIAL_REVS_DETECTED)

  @defer.deferredGenerator
  def test2_single_change(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self._modifySrcFile('git2', 'file2.txt', 'comment2')

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()
    self.assertEqual(
        len(self.poller.comparator.tag_order), INITIAL_REVS_DETECTED + 1,
        "%d total revisions after a single commit." %
        (INITIAL_REVS_DETECTED + 1))
    self.assertEqual(len(self.poller.master.changes), 1,
                     "One change in master")
    change = self.poller.master.changes[0][1]
    self.assertEqual(change['files'], ['file2.txt'],
                     'File(s) in change.')
    self.assertEqual(change['repository'], os.path.join(self.repo_src, 'git2'),
                     'Repository for change.')
    self.assertEqual(change['comments'], 'comment2',
                     'Change comments')

  @defer.deferredGenerator
  def test3_multiple_changes(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self._modifySrcFile('git1', 'file1.txt')

    d = task.deferLater(reactor, 2, self._modifySrcFile, 'git2', 'file2.txt', )
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    d = task.deferLater(reactor, 2, self._modifySrcFile, 'git0', 'file0.txt')
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self.assertEqual(
      len(self.poller.comparator.tag_order), INITIAL_REVS_DETECTED + 3,
      "%d total revisions after three commits." % (INITIAL_REVS_DETECTED + 3))
    self.assertEqual(len(self.poller.master.changes), 3,
                     "Three changes in master")
    self.assertEqual(self.poller.master.changes[0][1]['repository'],
                     os.path.join(self.repo_src, 'git0'),
                     'Commit ordering by timestamp')
    self.assertEqual(self.poller.master.changes[1][1]['repository'],
                     os.path.join(self.repo_src, 'git1'),
                     'Commit ordering by timestamp')
    self.assertEqual(self.poller.master.changes[2][1]['repository'],
                     os.path.join(self.repo_src, 'git2'),
                     'Commit ordering by timestamp')

  @defer.deferredGenerator
  def test4_stable_sort(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    # Create enough commits to make sure their are timestamp collisions
    for i in range(5):
      self._modifySrcFile('git1', 'file1.txt', 'c%d' % i)

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    comments = [change[1]['comments'] for change in self.poller.master.changes]
    self.assertEqual(comments, ['c%d' % i for i in range(5)],
                     'Stable sort')

  @defer.deferredGenerator
  def test5_err_notification(self):
    # Poll once to make sure working dir is initialized
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    # Trigger errors in polling by messing up working dir
    shutil.rmtree(os.path.join(self.repo_work, '.repo'))

    for i in range(1, 4):
      d = self.poller.poll()
      d.addErrback(lambda failure: True)
      wfd = defer.waitForDeferred(d)
      yield wfd
      wfd.getResult()
      self.assertEqual(self.poller.errCount, i * len(REPO_BRANCHES),
                       'Error count')

    self.assertEqual(len(SENT_MAILS), len(REPO_BRANCHES))
    self.assertEqual(SENT_MAILS[0][0:3],
                     ('nohost', 'sender@example.com', 'recipient@example.com'))

  @defer.deferredGenerator
  def test6_multiple_repo_branches(self):
    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    self._modifySrcFile('git1', 'file1.txt', branch='foo_branch')
    self._modifySrcFile('git2', 'file2.txt', branch='bar_branch')

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    ch1 = self.poller.master.changes[0][1]
    self.assertEqual(ch1['properties']['manifest_branch'], 'foo_branch')

    ch2 = self.poller.master.changes[1][1]
    self.assertEqual(ch2['properties']['manifest_branch'], 'bar_branch')

    # a second round of different changes
    self._modifySrcFile('git0', 'file0.txt', branch='bar_branch')
    self._modifySrcFile('git1', 'file1.txt', branch='master')

    d = self.poller.poll()
    wfd = defer.waitForDeferred(d)
    yield wfd
    wfd.getResult()

    # branches are polled in the order passed, in this case, REPO_BRANCHES'
    ch1 = self.poller.master.changes[2][1]
    self.assertEqual(ch1['properties']['manifest_branch'], 'master')

    ch2 = self.poller.master.changes[3][1]
    self.assertEqual(ch2['properties']['manifest_branch'], 'bar_branch')

## Helpers
def _cmd(tokens, cwd):
  with open(os.devnull, 'w') as devnull:
    code = subprocess.call(tokens, cwd=cwd, stdout=devnull, stderr=devnull)
  return code

if __name__ == '__main__':
  exe = os.path.join(os.path.dirname(twisted.__path__[0]), 'bin', 'trial')
  os.execv(exe, [exe, 'test_repo_poller'])
