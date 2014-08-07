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


class RevisionLinkTest(SuperMoxTestBase):
  def test_blink(self):
    revlink_fn = auto_roll.PROJECT_CONFIGS['blink']['revision_link_fn']
    expected = ('http://build.chromium.org/f/chromium/perf/dashboard/ui/'
                'changelog_blink.html?url=/trunk&range=%s:%s&mode=html') % (
                    1235, 1256)
    self.assertEqual(revlink_fn(1234, 1256), expected)

  def test_skia(self):
    revlink_fn = auto_roll.PROJECT_CONFIGS['skia']['revision_link_fn']
    expected = 'https://skia.googlesource.com/skia/+log/abc1234..def1256'
    self.assertEqual(revlink_fn('abc1234', 'def1256'), expected)


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

class AutoRollTestBase(SuperMoxTestBase):

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

  class MockHttpRpcServer(object):
    def __init__(self, *args, **kwargs):
      pass

  class MockDateTime(datetime.datetime):
    @classmethod
    def utcnow(cls):
      return AutoRollTestBase.MockDateTime(*AutoRollTestBase.CURRENT_DATETIME)

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
    self.mox.StubOutWithMock(auto_roll.subprocess2, 'check_call')
    self.mox.StubOutWithMock(auto_roll.subprocess2, 'check_output')
    self.mox.StubOutWithMock(auto_roll.urllib2, 'urlopen')
    auto_roll.datetime.datetime = self.MockDateTime
    auto_roll.rietveld.upload.HttpRpcServer = self.MockHttpRpcServer
    self._arb = auto_roll.AutoRoller(self.TEST_PROJECT,
                                     self.TEST_AUTHOR,
                                     self.PATH_TO_CHROME)

  def _make_issue(self, old_rev=None, new_rev=None, created_datetime=None):
    return {
        'author': self.TEST_AUTHOR,
        'commit': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'created': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'description': 'Test_Project roll %s:%s' % (self._display_rev(old_rev),
                                                    self._display_rev(new_rev)),
        'issue': 1234567,
        'messages': [],
        'modified': created_datetime or self.RECENT_ISSUE_CREATED_STR,
        'subject': 'Test_Project roll %s:%s' % (old_rev, new_rev),
    }

  def _get_last_revision(self):
    auto_roll.subprocess2.check_call(
        ['git', '--git-dir', './.git', 'fetch'])
    auto_roll.subprocess2.check_output(
        ['git', '--git-dir', './.git', 'show', 'origin/master:DEPS']
        ).AndReturn(self.DEPS_CONTENT)

  def _get_current_revision(self):
    auto_roll.subprocess2.check_call(
        ['git', '--git-dir', './third_party/test_project/.git', 'fetch'])
    if self._arb._git_mode:
      self._parse_origin_master(returnval=self.NEW_REV)
    else:
      auto_roll.subprocess2.check_output(
          ['git', '--git-dir', './third_party/test_project/.git', 'show', '-s',
           'origin/master']).AndReturn(self.GIT_LOG_UPDATED)

  def _upload_issue(self, custom_message=None):
    self._get_last_revision()
    self._get_current_revision()
    self._compare_revs(self.OLD_REV, self.NEW_REV)

    from_rev = self._display_rev(self.OLD_REV)
    to_rev = self._display_rev(self.NEW_REV)

    message = custom_message or 'Test_Project roll %s:%s' % (from_rev, to_rev)

    auto_roll.subprocess2.check_call(
        ['./tools/safely-roll-deps.py', self.TEST_PROJECT, str(self.NEW_REV),
         '--message', message, '--force'])
    issue = self._make_issue(created_datetime=self.CURRENT_DATETIME_STR)
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn([issue])
    self._arb._rietveld.add_comment(issue['issue'],
                                    self._arb.ROLL_BOT_INSTRUCTIONS)

  def test_should_stop(self):
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    issue = self._make_issue(created_datetime=self.OLD_ISSUE_CREATED_STR)
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
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    issue = self._make_issue()
    search_results = [issue]
    self._arb._rietveld.search(owner=self.TEST_AUTHOR,
                               closed=2).AndReturn(search_results)
    self._arb._rietveld.get_issue_properties(issue['issue'],
                                             messages=True).AndReturn(issue)
    auto_roll.subprocess2.check_call(
        ['git', '--git-dir', './.git', 'fetch'])
    auto_roll.subprocess2.check_output(
        ['git', '--git-dir', './.git', 'show', 'origin/master:DEPS']
        ).AndReturn(self.DEPS_CONTENT)
    if self._arb._git_mode:
      self._short_rev(self.OLD_REV)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)
    self.checkstdout('https://codereview.chromium.org/%d/ started %s ago\n'
                     'https://codereview.chromium.org/%d/ is still active, '
                     'nothing to do.\n'
                     % (issue['issue'], '0:59:59.900001', issue['issue']))

  def test_old_issue(self):
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    issue = self._make_issue(created_datetime=self.OLD_ISSUE_CREATED_STR)
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
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    issue = self._make_issue()
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
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    auto_roll.subprocess2.check_call(
        ['git', '--git-dir', './.git', 'fetch'])
    auto_roll.subprocess2.check_output(
        ['git', '--git-dir', './.git', 'show', 'origin/master:DEPS']
        ).AndReturn(self.DEPS_CONTENT)
    auto_roll.subprocess2.check_call(
        ['git', '--git-dir', './third_party/test_project/.git', 'fetch'])
    if self._arb._git_mode:
      auto_roll.subprocess2.check_output(
          ['git', '--git-dir', './third_party/test_project/.git', 'rev-parse',
           'origin/master']).AndReturn(self.OLDER_REV)
    else:
      auto_roll.subprocess2.check_output(
          ['git', '--git-dir', './third_party/test_project/.git', 'show', '-s',
           'origin/master']).AndReturn(self.GIT_LOG_TOO_OLD)
    self._compare_revs(self.OLD_REV, self.OLDER_REV)

    self.mox.ReplayAll()
    try:
      self._arb.main()
    except auto_roll.AutoRollException, e:
      self.assertEquals(e.args[0], ('Already at %s refusing to roll backwards '
                                    'to %s.') % (self.OLD_REV, self.OLDER_REV))

  def test_upload_issue(self):
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    self._upload_issue()
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)

  def test_last_revision(self):
    # Verify that AutoRoll._last_roll_revision() returns a string.
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    self._get_last_revision()
    self.mox.ReplayAll()
    self.assertEquals(type(self._arb._last_roll_revision()), str)

  def test_current_revision(self):
    # Verify that AutoRoll._current_revision() returns a string.
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    self._get_current_revision()
    self.mox.ReplayAll()
    self.assertEquals(type(self._arb._current_revision()), str)

  def test_extra_trybots(self):
    if self.__class__.__name__ == 'AutoRollTestBase':
      return
    self._arb._cq_extra_trybots = ['sometrybot']
    self._arb._rietveld.search(owner=self.TEST_AUTHOR, closed=2).AndReturn([])
    commit_msg = ('Test_Project roll %s:%s\n\nCQ_EXTRA_TRYBOTS=sometrybot' %
                  (self._display_rev(self.OLD_REV),
                   self._display_rev(self.NEW_REV)))
    self._upload_issue(custom_message=commit_msg)
    self.mox.ReplayAll()
    self.assertEquals(self._arb.main(), 0)


class AutoRollTestSVN(AutoRollTestBase):

  OLDER_REV = 1231
  OLD_REV = 1234
  NEW_REV = 1235

  DEPS_CONTENT = '''
vars = {
  "test_project_revision": "%d",
}
''' % OLD_REV

  _GIT_LOG = '''
commit abcde
Author: Test Author <test_author@example.com>
Date:   Wed Apr 2 14:00:14 2014 -0400

    Make some changes.

    git-svn-id: svn://svn.url/trunk@%d abcdefgh-abcd-abcd-abcd-abcdefghijkl
'''

  GIT_LOG_UPDATED = _GIT_LOG % NEW_REV
  GIT_LOG_TOO_OLD = _GIT_LOG % OLDER_REV

  def _make_issue(self, old_rev=None, new_rev=None, created_datetime=None):
    return AutoRollTestBase._make_issue(self,
                                        old_rev=old_rev or self.OLD_REV,
                                        new_rev=new_rev or self.NEW_REV,
                                        created_datetime=created_datetime)

  # pylint: disable=R0201
  def _display_rev(self, rev):
    return str(rev)

  # pylint: disable=R0201
  def _compare_revs(self, old_rev, new_rev):
    # Just an integer compare for SVN.
    pass

  # pylint: disable=R0201
  def _parse_origin_master(self, returnval):
    # Not required for SVN.
    pass


class AutoRollTestGit(AutoRollTestBase):

  OLDER_REV = 'cfcf604fbdcf6e2d9b982a2fab3fc9f1e3f8cd65'
  OLD_REV =   'b9af6489f6f2004ad11b82c6057f7007e3c35372'
  NEW_REV =   '79539998e04afab3ee9c3016881755ca52f60a73'

  DEPS_CONTENT = '''
vars = {
  "test_project_revision": "%s",
}
''' % OLD_REV

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

  def setUp(self):
    AutoRollTestBase.setUp(self)
    self._arb._git_mode = True

  def _make_issue(self, old_rev=None, new_rev=None, created_datetime=None):
    return AutoRollTestBase._make_issue(self,
                                        old_rev=old_rev or self.OLD_REV,
                                        new_rev=new_rev or self.NEW_REV,
                                        created_datetime=created_datetime)

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
    self._short_rev(old_rev)
    self._short_rev(new_rev)

  # pylint: disable=R0201
  def _parse_origin_master(self, returnval):
    auto_roll.subprocess2.check_output(
        ['git', '--git-dir', './third_party/test_project/.git', 'rev-parse',
         'origin/master']).AndReturn(returnval)


if __name__ == '__main__':
  unittest.main()
