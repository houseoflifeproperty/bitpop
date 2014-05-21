#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Integration tests for project.py."""

import logging
import os
import random
import shutil
import string
import StringIO
import sys
import tempfile
import time
import unittest
import urllib2

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

import projects
from verification import base
from verification import presubmit_check
from verification import try_job_on_rietveld

# From /tests
import mocks


def _try_comment(pc, issue=31337):
  return (
      "add_comment(%d, u'%shttp://localhost/user@example.com/%d/1\\n')" %
      (issue, pc.TRYING_PATCH.replace('\n', '\\n'),
        issue))


class CredentialsMock(object):
  def __init__(self, _):
    pass

  @staticmethod
  def get(user):
    return '1%s1' % user


class TestCase(mocks.TestCase):
  def setUp(self):
    super(TestCase, self).setUp()
    self.mock(projects.creds, 'Credentials', CredentialsMock)
    self.mock(projects, '_read_lines', self._read_lines)
    class Dummy(object):
      @staticmethod
      def get_list():
        return []
    if not projects.chromium_committers:
      projects.chromium_committers = Dummy()
    self.mock(
        projects.chromium_committers, 'get_list', self._get_committers_list)
    if not projects.nacl_committers:
      projects.nacl_committers = Dummy()
    self.mock(projects.nacl_committers, 'get_list', self._get_committers_list)
    self.mock(presubmit_check.subprocess2, 'check_output', self._check_output)
    self.mock(urllib2, 'urlopen', self._urlopen)
    self.mock(time, 'time', self._time)
    self.check_output = []
    self.read_lines = []
    self.urlrequests = []
    self.time = []

  def tearDown(self):
    if not self.has_failed():
      self.assertEqual([], self.check_output)
      self.assertEqual([], self.read_lines)
      self.assertEqual([], self.urlrequests)
      self.assertEqual([], self.time)
    super(TestCase, self).tearDown()

  # Mocks
  def _urlopen(self, url):
    if not self.urlrequests:
      self.fail(url)
    expected_url, data = self.urlrequests.pop(0)
    self.assertEqual(expected_url, url)
    return StringIO.StringIO(data)

  @staticmethod
  def _get_committers_list():
    return ['user@example.com', 'user@example.org']

  def _read_lines(self, root, error):
    if not self.read_lines:
      self.fail(root)
    a = self.read_lines.pop(0)
    self.assertEqual(a[0], root)
    self.assertEqual(a[1], error)
    return a[2]

  def _check_output(self, *args, **kwargs):
    # For now, ignore the arguments. Change if necessary.
    if not self.check_output:
      self.fail((args, kwargs))
    return self.check_output.pop(0)

  def _time(self):
    self.assertTrue(self.time)
    return self.time.pop(0)


class ProjectTest(TestCase):
  def setUp(self):
    super(ProjectTest, self).setUp()

  def test_loaded(self):
    members = (
        'chromium', 'chromium_deps', 'gyp', 'nacl', 'tools')
    self.assertEqual(sorted(members), sorted(projects.supported_projects()))

  def test_all(self):
    # Make sure it's possible to load each project.
    root_dir = os.path.join(os.getcwd(), 'root_dir')
    chromium_status_pwd = os.path.join(root_dir, '.chromium_status_pwd')
    mapping = {
      'chromium': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit', 'tree status'],
      },
      'chromium_deps': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit'],
      },
      'gyp': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['tree status'],
      },
      'nacl': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit', 'tree status'],
      },
      'tools': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit'],
      },
    }
    for project in sorted(projects.supported_projects()):
      logging.debug(project)
      self.assertEqual([], self.read_lines)
      expected = mapping.pop(project)
      self.read_lines = [expected['lines']]
      p = projects.load_project(
          project, 'user', root_dir, self.context.rietveld, True)
      self.assertEqual(
          expected['pre_patch_verifiers'],
          [x.name for x in p.pre_patch_verifiers],
          (expected['pre_patch_verifiers'],
           [x.name for x in p.pre_patch_verifiers],
           project))
      self.assertEqual(
          expected['verifiers'], [x.name for x in p.verifiers],
          (expected['verifiers'],
           [x.name for x in p.verifiers],
           project))
      if project == 'tools':
        # Add special checks for it.
        project_bases_verifier = p.pre_patch_verifiers[0]
        self.assertEqual(
            [
              # svn
              '^svn\\:\\/\\/svn\\.chromium\\.org\\/chrome/trunk/tools(|/.*)$',
              '^svn\\:\\/\\/chrome\\-svn\\/chrome/trunk/tools(|/.*)$',
              '^svn\\:\\/\\/chrome\\-svn\\.corp\\/chrome/trunk/tools(|/.*)$',
              '^svn\\:\\/\\/chrome\\-svn\\.corp\\.google\\.com\\/chrome/trunk/'
                  'tools(|/.*)$',
              '^http\\:\\/\\/src\\.chromium\\.org\\/svn/trunk/tools(|/.*)$',
              '^https\\:\\/\\/src\\.chromium\\.org\\/svn/trunk/tools(|/.*)$',
              '^http\\:\\/\\/src\\.chromium\\.org\\/chrome/trunk/tools(|/.*)$',
              '^https\\:\\/\\/src\\.chromium\\.org\\/chrome/trunk/tools(|/.*)$',

              # git
              '^http\\:\\/\\/git\\.chromium\\.org\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)\\.git\\@[a-zA-Z0-9\\-_]+$',
              '^https\\:\\/\\/git\\.chromium\\.org\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)\\.git\\@[a-zA-Z0-9\\-_]+$',
              '^http\\:\\/\\/git\\.chromium\\.org\\/git\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)\\@[a-zA-Z0-9\\-_]+$',
              '^https\\:\\/\\/git\\.chromium\\.org\\/git\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)\\@[a-zA-Z0-9\\-_]+$',
              '^http\\:\\/\\/git\\.chromium\\.org\\/git\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)\\.git\\@[a-zA-Z0-9\\-_]+$',
              '^https\\:\\/\\/git\\.chromium\\.org\\/git\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)\\.git\\@[a-zA-Z0-9\\-_]+$',
              '^https\\:\\/\\/chromium\\.googlesource\\.com\\/chromium\\/tools'
                  '\\/([a-z0-9\\-_]+)\\@[a-zA-Z0-9\\-_]+$',
              '^https\\:\\/\\/chromium\\.googlesource\\.com\\/chromium\\/tools'
                  '\\/([a-z0-9\\-_]+)\\.git\\@[a-zA-Z0-9\\-_]+$',
            ],
            project_bases_verifier.project_bases)
    self.assertEqual({}, mapping)


class ProjectChromiumTest(TestCase):
  def setUp(self):
    super(ProjectChromiumTest, self).setUp()

  def test_tbr(self):
    self.time = [1.] * 8
    self.urlrequests = [
      ('http://chromium-status.appspot.com/allstatus?format=json&endTime=-299',
        # Cheap hack here.
        '[]'),
    ]
    root_dir = os.path.join(os.getcwd(), 'root_dir')
    self.read_lines = [
        [
          os.path.join(root_dir, '.chromium_status_pwd'),
          'chromium-status password',
          ['foo'],
        ],
    ]
    pc = projects.load_project(
        'chromium', 'commit-bot-test', root_dir, self.context.rietveld, True)
    pc.context = self.context
    issue = self.context.rietveld.issues[31337]
    # A TBR= patch without reviewer nor messages, like a webkit roll.
    issue['description'] += '\nTBR='
    issue['reviewers'] = []
    issue['messages'] = []
    issue['owner_email'] = u'user@example.com'
    issue['base_url'] = u'svn://svn.chromium.org/chrome/trunk/src'
    pc.look_for_new_pending_commit()
    self.check_output = [0]
    pc.process_new_pending_commit()
    pc.update_status()
    pc.scan_results()
    self.assertEqual(0, len(pc.queue.pending_commits))
    self.context.rietveld.check_calls([
      _try_comment(pc),
      'close_issue(31337)',
      "update_description(31337, u'foo\\nTBR=')",
      "add_comment(31337, 'Change committed as 125')",
      ])
    self.context.checkout.check_calls([
      'prepare(None)',
      'apply_patch(%r)' % self.context.rietveld.patchsets[0],
      'prepare(None)',
      'apply_patch(%r)' % self.context.rietveld.patchsets[1],
      "commit(u'foo\\nTBR=\\n\\nReview URL: http://nowhere/31337', "
          "u'user@example.com')",
      ])
    self.context.status.check_names(['initial', 'commit'])


class ChromiumStateLoad(TestCase):
  # Load a complete state and ensure the code is reacting properly.
  def setUp(self):
    super(ChromiumStateLoad, self).setUp()
    self.buildbot = mocks.BuildbotMock(self)
    self.mock(
        try_job_on_rietveld.buildbot_json, 'Buildbot', lambda _: self.buildbot)
    self.tempdir = tempfile.mkdtemp(prefix='project_test')

  def tearDown(self):
    shutil.rmtree(self.tempdir)
    super(ChromiumStateLoad, self).tearDown()

  def _add_build(self, builder, buildnumber, revision, steps, completed):
    """Adds a build with a randomly generated key."""
    key = ''.join(random.choice(string.ascii_letters) for _ in xrange(8))
    build = self.buildbot.add_build(
        builder, buildnumber, revision, key, completed)
    build.steps.extend(steps)
    return key

  def testLoadState(self):
    # Loads a saved state and try to revive it.
    now = 1354207000.
    self.time = [now] * 27
    self.urlrequests = [
      ( 'http://chromium-status.appspot.com/allstatus?format=json&endTime=%d' %
            (now - 300),
        # Cheap hack here.
        '[]'),
    ]
    self.read_lines = [
        [
          os.path.join(self.tempdir, '.chromium_status_pwd'),
          'chromium-status password',
          ['foo'],
        ],
    ]

    self._add_build('ios_rel_device', 1, 2, [], 4)
    self.context.rietveld.patchsets_properties[(31337, 1)] = {}
    pc = projects.load_project(
        'chromium', 'invalid', self.tempdir, self.context.rietveld, False)
    pc.context = self.context
    # Do not use "chromium.json" because it's the default value.
    pc.load(os.path.join(ROOT_DIR, 'chromium_state.json'))
    # Verify the content a bit.
    self.assertEqual(1, len(pc.queue.pending_commits))
    self.assertEqual(31337, pc.queue.pending_commits[0].issue)
    expected = [
      u'presubmit',
      u'project_bases',
      u'reviewer_lgtm',
      u'tree status',
      u'try job rietveld',
    ]
    self.assertEqual(
        expected, sorted(pc.queue.pending_commits[0].verifications))
    # Then fix the crap out of it.
    pc.update_status()
    self.assertEqual(1, len(pc.queue.pending_commits))
    for name, obj in pc.queue.pending_commits[0].verifications.iteritems():
      if name == 'try job rietveld':
        self.assertEqual(base.PROCESSING, obj.get_state(), name)
        self.assertEqual(
            u'Waiting for the following jobs:\n'
            '  win_rel: sync_integration_tests\n',
            obj.why_not())
      else:
        self.assertEqual(base.SUCCEEDED, obj.get_state(), name)
        self.assertEqual(None, obj.why_not())
      self.assertEqual(False, obj.postpone(), name)
    self.context.rietveld.check_calls([])

  def testLoadState11299256(self):
    # Loads a saved state and try to revive it.
    now = 1354551606.
    issue = 11299256
    self.time = [now] * 27
    self.urlrequests = [
      ( 'http://chromium-status.appspot.com/allstatus?format=json&endTime=%d' %
            (now - 300),
        # In theory we should return something but nothing works fine.
        '[]'),
    ]
    self.read_lines = [
        [
          os.path.join(self.tempdir, '.chromium_status_pwd'),
          'chromium-status password',
          ['foo'],
        ],
    ]
    self._add_build('ios_rel_device', 1, 2, [], 4)
    self.context.rietveld.patchsets_properties[(issue, 1)] = {}
    pc = projects.load_project(
        'chromium', 'invalid', self.tempdir, self.context.rietveld, False)
    pc.context = self.context
    # Do not use "chromium.json" because it's the default value.
    pc.load(os.path.join(ROOT_DIR, 'chromium.%d.json' % issue))
    # Verify the content a bit.
    self.assertEqual(1, len(pc.queue.pending_commits))
    self.assertEqual(issue, pc.queue.pending_commits[0].issue)
    expected = [
      u'presubmit',
      u'project_bases',
      u'reviewer_lgtm',
      u'tree status',
      u'try job rietveld',
    ]
    self.assertEqual(
        expected, sorted(pc.queue.pending_commits[0].verifications))
    # Then fix the crap out of it.
    pc.update_status()
    self.assertEqual(1, len(pc.queue.pending_commits))
    for name, obj in pc.queue.pending_commits[0].verifications.iteritems():
      if name == 'try job rietveld':
        # TODO(maruel): This is wrong, fix me.
        self.assertEqual(base.PROCESSING, obj.get_state(), name)
        self.assertEqual(
            u'Waiting for the following jobs:\n'
            '  ios_rel_device: compile\n',
            obj.why_not())
      else:
        self.assertEqual(base.SUCCEEDED, obj.get_state(), name)
        self.assertEqual(None, obj.why_not())
      self.assertEqual(False, obj.postpone(), name)
    self.context.rietveld.check_calls(
        [
          "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'ios_rel_device': "
              "[u'compile']})" % issue
        ])


if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.WARNING,
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
