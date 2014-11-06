#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Automates creation and management of DEPS roll CLs.

This script is designed to be run in a loop (eg. with auto_roll_wrapper.sh) or
on a timer. It may take one of several actions, depending on the state of
in-progress DEPS roll CLs and the state of the repository:

- If there is already a DEPS roll CL in the Commit Queue, just exit.
- If there is an open DEPS roll CL which is not in the Commit Queue:
    - If there's a comment containing the "STOP" keyword, just exit.
    - Otherwise, close the issue and continue.
- If there is no open DEPS roll CL, create one using the
    src/tools/safely-roll-deps.py script.
"""


import datetime
import json
import optparse
import os.path
import re
import sys
import textwrap
import urllib2


SCRIPTS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                            os.pardir, os.pardir))
sys.path.insert(0, SCRIPTS_DIR)

# pylint: disable=W0611
from common import find_depot_tools

import rietveld
import roll_dep
import scm
import subprocess2


BLINK_SHERIFF_URL = (
  'http://build.chromium.org/p/chromium.webkit/sheriff_webkit.js')
CHROMIUM_SHERIFF_URL = (
  'http://build.chromium.org/p/chromium.webkit/sheriff.js')

CQ_EXTRA_TRYBOTS = 'CQ_EXTRA_TRYBOTS='

# Does not support unicode or special characters.
VALID_EMAIL_REGEXP = re.compile(r'^[A-Za-z0-9\.&\'\+-/=_]+@'
                                '[A-Za-z0-9\.-]+$')


def _get_skia_sheriff():
  """Finds and returns the current Skia sheriff."""
  skia_sheriff_url = 'https://skia-tree-status.appspot.com/current-sheriff'
  return json.load(urllib2.urlopen(skia_sheriff_url))['username']


def _complete_email(name):
  """If the name does not include '@', append '@chromium.org'."""
  if '@' not in name:
    return name + '@chromium.org'
  return name


def _names_from_sheriff_js(sheriff_js):
  match = re.match(r'document.write\(\'(.*)\'\)', sheriff_js)
  emails_string = match.group(1)
  # Detect 'none (channel is sheriff)' text and ignore it.
  if 'channel is sheriff' in emails_string.lower():
    return []
  return map(str.strip, emails_string.split(','))


def _email_is_valid(email):
  """Determines whether the given email address is valid."""
  return VALID_EMAIL_REGEXP.match(email) is not None


def _filter_emails(emails):
  """Returns the given list with any invalid email addresses removed."""
  rv = []
  for email in emails:
    if _email_is_valid(email):
      rv.append(email)
    else:
      print 'WARNING: Not including %s (invalid email address)' % email
  return rv


def _emails_from_url(sheriff_url):
  sheriff_js = urllib2.urlopen(sheriff_url).read()
  return map(_complete_email, _names_from_sheriff_js(sheriff_js))


def _current_gardener_emails():
  return _emails_from_url(BLINK_SHERIFF_URL)


def _current_sheriff_emails():
  return _emails_from_url(CHROMIUM_SHERIFF_URL)


def _do_git_fetch(git_dir):
  subprocess2.check_call(['git', '--git-dir', git_dir, 'fetch'])


PROJECT_CONFIGS = {
  'blink': {
    'extra_emails_fn': _current_gardener_emails,
    'path_to_project': os.path.join('third_party', 'WebKit'),
    'project_alias': 'webkit',
  },
  'skia': {
    'cq_extra_trybots': ['tryserver.blink:linux_blink_rel,linux_blink_dbg'],
    'extra_emails_fn': lambda: [_get_skia_sheriff()],
    'path_to_project': os.path.join('third_party', 'skia'),
  },
}


class AutoRollException(Exception):
  pass


class AutoRoller(object):
  RIETVELD_URL = 'https://codereview.chromium.org'
  RIETVELD_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
  ROLL_TIME_LIMIT = datetime.timedelta(hours=24)
  STOP_NAG_TIME_LIMIT = datetime.timedelta(hours=12)
  ADMIN_EMAIL = 'eseidel@chromium.org'

  ROLL_DESCRIPTION_REGEXP = roll_dep.ROLL_DESCRIPTION_STR % {
    'dep_path': '%(project)s',
    'before_rev': '(?P<from_revision>[0-9a-fA-F]{2,40})',
    'after_rev': '(?P<to_revision>[0-9a-fA-F]{2,40})',
    'svn_range': '.*',
    'revlog_url': '.+',
  }

  # FIXME: These are taken from gardeningserver.py and should be shared.
  CHROMIUM_SVN_DEPS_URL = 'http://src.chromium.org/chrome/trunk/src/DEPS'

  ROLL_BOT_INSTRUCTIONS = textwrap.dedent(
    '''This roll was created by the Blink AutoRollBot.
    http://www.chromium.org/blink/blinkrollbot''')

  PLEASE_RESUME_NAG = textwrap.dedent('''
    Rollbot was stopped by the presence of 'STOP' in an earlier comment.
    The last update to this issue was over %(stop_nag_timeout)s hours ago.
    Please close this issue as soon as possible to allow the bot to continue.

    Please email (%(admin)s) if the Rollbot is causing trouble.
    ''' % {'admin': ADMIN_EMAIL, 'stop_nag_timeout': STOP_NAG_TIME_LIMIT})

  def __init__(self, project, author, path_to_chrome):
    self._author = author
    self._project = project
    self._path_to_chrome = path_to_chrome
    self._rietveld = rietveld.Rietveld(
      self.RIETVELD_URL, self._author, None)
    self._cached_last_roll_revision = None

    project_config = PROJECT_CONFIGS.get(self._project, {
      'path_to_project': os.path.join('third_party', self._project),
    })
    self._project_alias = project_config.get('project_alias', self._project)
    self._path_to_project = project_config['path_to_project']
    self._get_extra_emails = project_config.get('extra_emails_fn', lambda: [])
    self._cq_extra_trybots = project_config.get('cq_extra_trybots', [])

    self._chromium_git_dir = self._path_from_chromium_root('.git')
    self._project_git_dir = self._path_from_chromium_root(
        self._path_to_project, '.git')
    self._roll_description_regexp = (self.ROLL_DESCRIPTION_REGEXP % {
        'project': 'src/' + self._path_to_project
    }).splitlines()[0]

  def _parse_time(self, time_string):
    return datetime.datetime.strptime(time_string, self.RIETVELD_TIME_FORMAT)

  def _url_for_issue(self, issue_number):
    return '%s/%d/' % (self.RIETVELD_URL, issue_number)

  def _search_for_active_roll(self):
    # FIXME: Rietveld.search is broken, we should use closed=False
    # but that sends closed=1, we want closed=3.  Using closed=2
    # to that search translates it correctly to closed=3 internally.
    # https://code.google.com/p/chromium/issues/detail?id=242628
    for result in self._rietveld.search(owner=self._author, closed=2):
      if re.search(self._roll_description_regexp, result['subject']):
        return result
    return None

  def _rollbot_should_stop(self, issue):
    issue_number = issue['issue']
    for message in issue['messages']:
      if 'STOP' in message['text']:
        last_modified = self._parse_time(issue['modified'])
        time_since_last_comment = datetime.datetime.utcnow() - last_modified
        if time_since_last_comment > self.STOP_NAG_TIME_LIMIT:
          self._rietveld.add_comment(issue_number, self.PLEASE_RESUME_NAG)

        print '%s: Rollbot was stopped by %s on at %s, waiting.' % (
          self._url_for_issue(issue_number), message['sender'], message['date'])
        return True
    return False

  def _close_issue(self, issue_number, message=None):
    print 'Closing %s with message: \'%s\'' % (
      self._url_for_issue(issue_number), message)
    if message:
      self._rietveld.add_comment(issue_number, message)
    self._rietveld.close_issue(issue_number)

  def _path_from_chromium_root(self, *components):
    assert os.pardir not in components
    return os.path.join(self._path_to_chrome, *components)

  def _last_roll_revision(self):
    """Returns the revision of the last roll.

    Returns:
        revision of the last roll; either a 40-character Git commit hash or an
        SVN revision number.
    """
    if not self._cached_last_roll_revision:
      revinfo = subprocess2.check_output(['gclient', 'revinfo'],
                                         cwd=self._path_to_chrome)
      project_path = 'src/' + self._path_to_project
      for line in revinfo.splitlines():
        dep_path, source = line.split(': ', 1)
        if dep_path == project_path:
          self._cached_last_roll_revision = source.split('@')[-1]
          break
      assert len(self._cached_last_roll_revision) == 40
    return self._cached_last_roll_revision

  def _current_revision(self):
    git_revparse_cmd = ['git', '--git-dir', self._project_git_dir,
                        'rev-parse', 'origin/master']
    return subprocess2.check_output(git_revparse_cmd).rstrip()

  def _emails_to_cc_on_rolls(self):
    return _filter_emails(self._get_extra_emails())

  def _start_roll(self, new_roll_revision):
    roll_branch = '%s_roll' % self._project
    cwd_kwargs = {'cwd': self._path_to_chrome}
    subprocess2.check_call(['git', 'clean', '-d', '-f'], **cwd_kwargs)
    subprocess2.call(['git', 'rebase', '--abort'], **cwd_kwargs)
    subprocess2.call(['git', 'branch', '-D', roll_branch], **cwd_kwargs)
    subprocess2.check_call(['git', 'checkout', 'origin/master', '-f'],
                           **cwd_kwargs)
    subprocess2.check_call(['git', 'checkout', '-b', roll_branch,
                            '-t', 'origin/master', '-f'], **cwd_kwargs)
    try:
      subprocess2.check_call(['roll-dep', self._path_to_project,
                              new_roll_revision], **cwd_kwargs)
      subprocess2.check_call(['git', 'add', 'DEPS'], **cwd_kwargs)
      subprocess2.check_call(['git', 'commit', '--no-edit'], **cwd_kwargs)
      commit_msg = subprocess2.check_output(['git', 'log', '-n1', '--format=%B',
                                             'HEAD'], **cwd_kwargs)

      upload_cmd = ['git', 'cl', 'upload', '--bypass-hooks',
                    '--use-commit-queue', '-f']
      if self._cq_extra_trybots:
        commit_msg += ('\n\n' + CQ_EXTRA_TRYBOTS +
                       ','.join(self._cq_extra_trybots))
      tbr = '\nTBR='
      emails = self._emails_to_cc_on_rolls()
      if emails:
        emails_str = ','.join(emails)
        tbr += emails_str
        upload_cmd.extend(['--cc', emails_str, '--send-mail'])
      commit_msg += tbr
      upload_cmd.extend(['-m', commit_msg])
      subprocess2.check_call(upload_cmd, **cwd_kwargs)
    finally:
      subprocess2.check_call(['git', 'checkout', 'origin/master', '-f'],
                             **cwd_kwargs)
      subprocess2.check_call(
          ['git', 'branch', '-D', roll_branch], **cwd_kwargs)

    # FIXME: It's easier to pull the issue id from rietveld rather than
    # parse it from the safely-roll-deps output.  Once we inline
    # safely-roll-deps into this script this can go away.
    search_result = self._search_for_active_roll()
    if search_result:
      self._rietveld.add_comment(search_result['issue'],
          self.ROLL_BOT_INSTRUCTIONS)

  def _maybe_close_active_roll(self, issue):
    issue_number = issue['issue']

    # If the CQ failed, this roll is DOA.
    if not issue['commit']:
      self._close_issue(
          issue_number,
          'No longer marked for the CQ. Closing, will open a new roll.')
      return True

    create_time = self._parse_time(issue['created'])
    time_since_roll = datetime.datetime.utcnow() - create_time
    print '%s started %s ago' % (
      self._url_for_issue(issue_number), time_since_roll)
    if time_since_roll > self.ROLL_TIME_LIMIT:
      self._close_issue(
          issue_number,
          'Giving up on this roll after %s. Closing, will open a new roll.' %
          self.ROLL_TIME_LIMIT)
      return True

    last_roll_revision = self._short_rev(self._last_roll_revision())
    match = re.match(self._roll_description_regexp, issue['subject'])
    if match.group('from_revision') != last_roll_revision:
      self._close_issue(
          issue_number,
          'DEPS has already rolled to %s. Closing, will open a new roll.' %
          last_roll_revision)
      return True

    return False

  def _compare_revisions(self, last_roll_revision, new_roll_revision):
    """Ensure that new_roll_revision is newer than last_roll_revision."""
    # Ensure that new_roll_revision is not an ancestor of old_roll_revision.
    try:
      subprocess2.check_call(['git', '--git-dir', self._project_git_dir,
                              'merge-base', '--is-ancestor',
                              new_roll_revision, last_roll_revision])
      print ('Already at %s refusing to roll backwards to %s.' % (
                 last_roll_revision, new_roll_revision))
      return False
    except subprocess2.CalledProcessError:
      pass
    return True

  def _short_rev(self, revision):
    """Shorten a Git commit hash."""
    return subprocess2.check_output(['git', '--git-dir', self._project_git_dir,
                                     'rev-parse', '--short', revision]
                                    ).rstrip()

  def main(self):
    _do_git_fetch(self._chromium_git_dir)
    _do_git_fetch(self._project_git_dir)

    search_result = self._search_for_active_roll()
    issue_number = search_result['issue'] if search_result else None
    if issue_number:
      issue = self._rietveld.get_issue_properties(issue_number, messages=True)
    else:
      issue = None

    if issue:
      if self._rollbot_should_stop(issue):
        return 1
      if not self._maybe_close_active_roll(issue):
        print '%s is still active, nothing to do.' % \
            self._url_for_issue(issue_number)
        return 0

    last_roll_revision = self._last_roll_revision()
    new_roll_revision = self._current_revision()

    if not new_roll_revision:
      raise AutoRollException(
          'Could not determine the current revision.')

    if not self._compare_revisions(last_roll_revision, new_roll_revision):
      return 0

    self._start_roll(new_roll_revision)
    return 0


def main():
  usage = 'Usage: %prog project_name author path_to_chromium'

  # The default HelpFormatter causes the docstring to display improperly.
  class VanillaHelpFormatter(optparse.IndentedHelpFormatter):
    def format_description(self, description):
      if description:
        return description
      else:
        return ''

  parser = optparse.OptionParser(usage=usage,
                                 description=sys.modules[__name__].__doc__,
                                 formatter=VanillaHelpFormatter())
  _, args = parser.parse_args()
  if len(args) != 3:
    parser.print_usage()
    return 1

  AutoRoller(*args).main()


if __name__ == '__main__':
  sys.exit(main())
