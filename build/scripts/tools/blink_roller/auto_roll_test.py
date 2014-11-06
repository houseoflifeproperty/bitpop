#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import datetime
import unittest

import auto_roll

# auto_roll.py imports find_depot_tools.
from testing_support.super_mox import SuperMoxTestBase


# pylint: disable=W0212


def _do_fetches():
  auto_roll.subprocess2.check_call(
      ['git', '--git-dir', './.git', 'fetch'])
  auto_roll.subprocess2.check_call(
      ['git', '--git-dir', './third_party/test_project/.git', 'fetch'])


class SheriffCalendarTest(SuperMoxTestBase):

  def test_complete_email(self):
    expected_emails = ['foo@chromium.org', 'bar@google.com', 'baz@chromium.org']
    names = ['foo', 'bar@google.com', 'baz']
    self.assertEqual(map(auto_roll._complete_email, names), expected_emails)

  def test_emails(self):
    expected_emails = ['foo@bar.com', 'baz@baz.com']
    auto_roll._emails_from_url = lambda urls: expected_emails
    self.assertEqual(auto_roll._current_gardener_emails(), expected_emails)
    self.assertEqual(auto_roll._current_sheriff_emails(), expected_emails)

  def _assert_parse(self, js_string, expected_emails):
    self.assertEqual(
      auto_roll._names_from_sheriff_js(js_string), expected_emails)

  def test_names_from_sheriff_js(self):
    self._assert_parse('document.write(\'none (channel is sheriff)\')', [])
    self._assert_parse('document.write(\'foo, bar\')', ['foo', 'bar'])

  def test_email_regexp(self):
    self.assertTrue(auto_roll._email_is_valid('somebody@example.com'))
    self.assertTrue(auto_roll._email_is_valid('somebody@example.domain.com'))
    self.assertTrue(auto_roll._email_is_valid('somebody@example-domain.com'))
    self.assertTrue(auto_roll._email_is_valid('some.body@example.com'))
    self.assertTrue(auto_roll._email_is_valid('some_body@example.com'))
    self.assertTrue(auto_roll._email_is_valid('some+body@example.com'))
    self.assertTrue(auto_roll._email_is_valid('some+body@com'))
    self.assertTrue(auto_roll._email_is_valid('some/body@example.com'))
    # These are valid according to the standard, but not supported here.
    self.assertFalse(auto_roll._email_is_valid('some~body@example.com'))
    self.assertFalse(auto_roll._email_is_valid('some!body@example.com'))
    self.assertFalse(auto_roll._email_is_valid('some?body@example.com'))
    self.assertFalse(auto_roll._email_is_valid('some" "body@example.com'))
    self.assertFalse(auto_roll._email_is_valid('"{somebody}"@example.com'))
    # Bogus.
    self.assertFalse(auto_roll._email_is_valid('rm -rf /#@example.com'))
    self.assertFalse(auto_roll._email_is_valid('some body@example.com'))
    self.assertFalse(auto_roll._email_is_valid('[some body]@example.com'))

  def test_filter_emails(self):
    input_emails = ['foo@bar.com', 'baz@baz.com', 'bogus email @ !!!']
    expected_emails = ['foo@bar.com', 'baz@baz.com']
    self.assertEquals(auto_roll._filter_emails(input_emails), expected_emails)
    self.checkstdout('WARNING: Not including bogus email @ !!! '
                     '(invalid email address)\n')

class AutoRollTest(SuperMoxTestBase):

  TEST_PROJECT = 'test_project'
  TEST_AUTHOR = 'test_author@chromium.org'
  PATH_TO_CHROME = '.'

  DATETIME_FORMAT = '%d-%d-%d %d:%d:%d.%d'
  CURRENT_DATETIME = (2014, 4, 1, 14, 57, 21, 01)
  RECENT_ISSUE_CREATED = (2014, 4, 1, 13, 57, 21, 01)
  OLD_ISSUE_CREATED = (2014, 2, 1, 13, 57, 21, 01)
  CURRENT_DATETIME_STR = DATETIME_FORMAT % CURRENT_DATETIME
  RECENT_ISSUE_CREATED_STR = DATETIME_FORMAT % RECENT_ISSUE_CREATED
  OLD_ISSUE_CREATED_STR = DATETIME_FORMAT % OLD_ISSUE_CREATED

  OLDER_REV = 'cfcf604fbdcf6e2d9b982a2fab3fc9f1e3f8cd65'
  OLD_REV =   'b9af6489f6f2004ad11b82c6057f7007e3c35372'
  NEW_REV =   '79539998e04afab3ee9c3016881755ca52f60a73'

  _GIT_LOG = '''
commit %s
Author: Test Author <test_author@example.com>
Date:   Wed Apr 2 14:00:14 2014 -0400

    Make some changes.
'''
  GIT_LOG_UPDATED = _GIT_LOG % NEW_REV
  GIT_LOG_TOO_OLD = _GIT_LOG % OLDER_REV

  _commit_timestamps = {
    OLDER_REV: '1399573100',
    OLD_REV: '1399573342',
    NEW_REV: '1399598876',
  }

  class MockHttpRpcServer(object):
    def __init__(self, *args, **kwargs):
      pass

  class MockDateTime(datetime.datetime):
    @classmethod
    def utcnow(cls):
      return AutoRollTest.MockDateTime(*AutoRollTest.CURRENT_DATETIME)

  class MockFile(object):
    def __init__(self, contents):
      self._contents = contents

    def read(self):
      return self._contents

  def setUp(self):
    SuperMoxTestBase.setUp(self)
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld, 'add_comment')
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld, 'close_issue')
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld,
                             'get_issue_properties')
    self.mox.StubOutWithMock(auto_roll.rietveld.Rietveld, 'search')
    self.mox.StubOutWithMock(auto_roll.scm.GIT, 'Capture')
    self.mox.StubOutWithMock(auto_roll.subprocess2, 'call')
    self.mox.StubOutWithMock(auto_roll.subprocess2, 'check_call')
    self.mox.StubOutWithMock(auto_roll.subprocess2, 'check_output')
    self.mox.StubOutWithMock(auto_roll.urllib2, 'urlopen')
    auto_roll.datetime.datetime = self.MockDateTime
    auto_roll.rietveld.upload.HttpRpcServer = self.MockHttpRpcServer
    self._arb = auto_roll.AutoRoller(self.TEST_PROJECT,
                                     self.TEST_AUTHOR,
                                     self.PATH_TO_CHROME)

  def _make_issue(self, old_rev, new_rev, created_datetime=None,
                  svn_range_str=''):
    description = auto_roll.roll_dep.ROLL_DESCRIPTION_STR % {
        'dep_path': 'src/third_party/test_project',
        'before_rev': self._display_rev(old_rev),
        'after_rev': self._display_rev(new_rev),
        'svn_range': svn_range_str,
        'revlog_url': '',
    }
    return {
        'author': self.TEST_AUTHOR,
        'commit': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'created': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'description': description,
        'issue': 1234567,
        'messages': [],
        'modified': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'subject': description.splitlines()[0],
    }

  def _get_last_revision(self):
    revinfo = (
        'src/third_party/test_project: '
        'https://chromium.googlesource.com/test_project.git@%s' %
            str(self.OLD_REV))
    auto_roll.subprocess2.check_output(['gclient', 'revinfo'],
                                       cwd='.').AndReturn(revinfo)

  def _get_current_revision(self):
    self._parse_origin_master(returnval=self.NEW_REV)

  def _upload_issue(self, custom_message=None):
    _do_fetches()

    self._get_last_revision()
    self._get_current_revision()

    self._compare_revs(self.OLD_REV, self.NEW_REV)

    auto_roll.subprocess2.check_call(['git', 'clean', '-d', '-f'], cwd='.')
    auto_roll.subprocess2.call(['git', 'rebase', '--abort'], cwd='.')
    auto_roll.subprocess2.call(['git', 'branch', '-D', 'test_project_roll'],
                               cwd='.')
    auto_roll.subprocess2.check_call(['git', 'checkout', 'origin/master', '-f'],
                                     cwd='.')
    auto_roll.subprocess2.check_call(['git', 'checkout',
                                      '-b', 'test_project_roll',
                                      '-t', 'origin/master', '-f'], cwd='.')

    issue = self._make_issue(self.OLD_REV, self.NEW_REV,
                             created_datetime=self.CURRENT_DATETIME_STR)

    if custom_message:
      message = custom_message
    else:
      message = issue['description']

    message += '\nTBR='
    auto_roll.subprocess2.check_call(
        ['roll-dep', 'third_party/%s' % self.TEST_PROJECT, str(self.NEW_REV)],
        cwd='.')

    auto_roll.subprocess2.check_call(['git', 'add', 'DEPS'], cwd='.')
    auto_roll.subprocess2.check_call(['git', 'commit', '--no-edit'], cwd='.')
    auto_roll.subprocess2.check_output(
        ['git', 'log', '-n1', '--format=%B', 'HEAD'],
        cwd='.').AndReturn(issue['description'])
    auto_roll.subprocess2.check_call(['git', 'cl', 'upload', '--bypass-hooks',
                                      '--use-commit-queue', '-f',
                                      '-m', message],
                                     cwd='.')
    auto_roll.subprocess2.check_call(['git', 'checkout', 'origin/master', '-f'],
                                     cwd='.')
    auto_roll.subprocess2.check_call(['git', 'branch', '-D',
                                      'test_project_roll'], cwd='.')

    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn([issue])
    self._arb._rietveld.add_comment(issue['issue'],
                                    self._arb.ROLL_BOT_INSTRUCTIONS)

  def test_should_stop(self):
    _do_fetches()
    issue = self._make_issue(self.OLD_REV, self.NEW_REV,
                             created_datetime=self.OLD_ISSUE_CREATED_STR)
    issue['messages'].append({
        'text': 'STOP',
        'sender': self.TEST_AUTHOR,
        'date': '2014-3-31 13:57:21.01'
    })
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    self._arb._rietveld.add_comment(issue['issue'], '''
Rollbot was stopped by the presence of 'STOP' in an earlier comment.
The last update to this issue was over 12:00:00 hours ago.
Please close this issue as soon as possible to allow the bot to continue.

Please email (eseidel@chromium.org) if the Rollbot is causing trouble.
''')

    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 1)
    self.checkstdout('https://codereview.chromium.org/%d/: Rollbot was '
                     'stopped by test_author@chromium.org on at 2014-3-31 '
                     '13:57:21.01, waiting.\n' % issue['issue'])

  def test_already_rolling(self):
    _do_fetches()
    issue = self._make_issue(self.OLD_REV, self.NEW_REV)
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    self._get_last_revision()
    self._short_rev(self.OLD_REV)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)
    self.checkstdout('https://codereview.chromium.org/%d/ started %s ago\n'
                     'https://codereview.chromium.org/%d/ is still active, '
                     'nothing to do.\n'
                     % (issue['issue'], '0:59:59.900001', issue['issue']))

  def test_old_issue(self):
    issue = self._make_issue(self.OLD_REV, self.NEW_REV,
                             created_datetime=self.OLD_ISSUE_CREATED_STR)
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    comment_str = ('Giving up on this roll after 1 day, 0:00:00. Closing, will '
                   'open a new roll.')
    self._arb._rietveld.add_comment(issue['issue'], comment_str)
    self._arb._rietveld.close_issue(issue['issue'])
    self._upload_issue()
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)
    self.checkstdout('https://codereview.chromium.org/%d/ started %s ago\n'
                     'Closing https://codereview.chromium.org/%d/ with message:'
                     ' \'%s\'\n'
                     % (issue['issue'], '59 days, 0:59:59.900001',
                        issue['issue'], comment_str))

  def test_failed_cq(self):
    issue = self._make_issue(self.OLD_REV, self.NEW_REV)
    issue['commit'] = False
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    comment_str = 'No longer marked for the CQ. Closing, will open a new roll.'
    self._arb._rietveld.add_comment(issue['issue'], comment_str)
    self._arb._rietveld.close_issue(issue['issue'])
    self._upload_issue()
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)
    self.checkstdout('Closing https://codereview.chromium.org/%d/ with message:'
                     ' \'%s\'\n' % (issue['issue'], comment_str))

  def test_no_roll_backwards(self):
    _do_fetches()
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    self._get_last_revision()
    auto_roll.subprocess2.check_output(
        ['git', '--git-dir', './third_party/test_project/.git', 'rev-parse',
         'origin/master']).AndReturn(self.OLDER_REV)
    self._compare_revs(self.OLD_REV, self.OLDER_REV)

    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)
    self.checkstdout('Already at %s refusing to roll backwards to %s.\n' % (
                         self.OLD_REV, self.OLDER_REV))

  def test_upload_issue(self):
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    self._upload_issue()
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)

  def test_last_revision(self):
    # Verify that AutoRoll._last_roll_revision() returns a string.
    self._get_last_revision()
    self.mox.ReplayAll()
    self.assertEquals(type(self._arb._last_roll_revision()), str)

  def test_current_revision(self):
    # Verify that AutoRoll._current_revision() returns a string.
    self._get_current_revision()
    self.mox.ReplayAll()
    self.assertEquals(type(self._arb._current_revision()), str)

  def test_extra_trybots(self):
    self._arb._cq_extra_trybots = ['sometrybot']
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    svn_range_str = ''
    commit_msg = self._make_issue(self.OLD_REV, self.NEW_REV,
                                  svn_range_str=svn_range_str)['description']
    commit_msg += '\n\nCQ_EXTRA_TRYBOTS=sometrybot'
    self._upload_issue(custom_message=commit_msg)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)

  # pylint: disable=R0201
  def _display_rev(self, rev):
    return rev[:7]

  # pylint: disable=R0201
  def _short_rev(self, rev):
    auto_roll.subprocess2.check_output(['git', '--git-dir',
                                        './third_party/test_project/.git',
                                        'rev-parse', '--short', rev]
                                       ).AndReturn(self._display_rev(rev))

  def _compare_revs(self, old_rev, new_rev):
    merge_base_cmd = ['git', '--git-dir', './third_party/test_project/.git',
                      'merge-base', '--is-ancestor', new_rev, old_rev]
    if self._commit_timestamps[old_rev] < self._commit_timestamps[new_rev]:
      err = auto_roll.subprocess2.CalledProcessError(1, '', '', '', '')
      auto_roll.subprocess2.check_call(merge_base_cmd).AndRaise(err)
    else:
      auto_roll.subprocess2.check_call(merge_base_cmd)
      return

  # pylint: disable=R0201
  def _parse_origin_master(self, returnval):
    auto_roll.subprocess2.check_output(
        ['git', '--git-dir', './third_party/test_project/.git', 'rev-parse',
         'origin/master']).AndReturn(returnval)


if __name__ == '__main__':
  unittest.main()
