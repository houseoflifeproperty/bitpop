# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Recipe for the Skia AutoRoll Bot."""


import re
from common.skia import global_constants


DEPS = [
  'file',
  'gclient',
  'gsutil',
  'path',
  'raw_io',
  'step',
]


DEPS_ROLL_AUTHOR = 'skia-deps-roller@chromium.org'
DEPS_ROLL_NAME = 'Skia DEPS Roller'
HTML_CONTENT = '''
<html>
<head>
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="-1">
<meta http-equiv="refresh" content="0; url=%s" />
</head>
</html>
'''
ISSUE_URL_TEMPLATE = 'https://codereview.chromium.org/%(issue)s/'
# TODO(borenet): Find a way to share these filenames (or their full GS URL) with
# the webstatus which links to them.
FILENAME_CURRENT_ATTEMPT = 'depsroll.html'
FILENAME_ROLL_STATUS = 'arb_status.html'

REGEXP_ISSUE_CREATED = (
    r'Issue created. URL: https://codereview.chromium.org/(?P<issue>\d+)')
REGEXP_ROLL_ACTIVE = (
    r'https://codereview.chromium.org/(?P<issue>\d+)/ is still active')
REGEXP_ROLL_STOPPED = (
    r'https://codereview.chromium.org/(?P<issue>\d+)/: Rollbot was stopped by')
# This occurs when the ARB has "caught up" and has nothing new to roll, or when
# a different roll (typically a manual roll) has already rolled past it.
REGEXP_ROLL_TOO_OLD = r'Already at .+ refusing to roll backwards to .+'
ROLL_STATUS_IN_PROGRESS = 'In progress - %s' % ISSUE_URL_TEMPLATE
ROLL_STATUS_STOPPED = 'Stopped - %s' % ISSUE_URL_TEMPLATE
ROLL_STATUS_IDLE = 'Idle'
ROLL_STATUSES = [
    (REGEXP_ISSUE_CREATED, ROLL_STATUS_IN_PROGRESS),
    (REGEXP_ROLL_ACTIVE,   ROLL_STATUS_IN_PROGRESS),
    (REGEXP_ROLL_STOPPED,  ROLL_STATUS_STOPPED),
    (REGEXP_ROLL_TOO_OLD,  ROLL_STATUS_IDLE),
]


def GenSteps(api):
  # Check out Chrome.
  gclient_cfg = api.gclient.make_config()
  s = gclient_cfg.solutions.add()
  s.name = 'src'
  s.url = 'https://chromium.googlesource.com/chromium/src.git'
  # This isn't strictly required, but sometimes chromium.googlesource.com/skia
  # lags behind.  We'd rather be as up-to-date as possible in our rolls.
  s.custom_deps['src/third_party/skia'] = (
      'https://skia.googlesource.com/skia.git')
  gclient_cfg.got_revision_mapping['src/third_party/skia'] = 'got_revision'

  api.gclient.checkout(gclient_config=gclient_cfg)

  src_dir = api.path['checkout']
  api.step('git config user.name',
           ['git', 'config', '--local', 'user.name', DEPS_ROLL_NAME],
           cwd=src_dir)
  api.step('git config user.email',
           ['git', 'config', '--local', 'user.email', DEPS_ROLL_AUTHOR],
           cwd=src_dir)

  auto_roll = api.path['build'].join('scripts', 'tools', 'blink_roller',
                                     'auto_roll.py')
  error = None
  try:
    output = api.step(
        'do auto_roll',
        ['python', auto_roll, 'skia', DEPS_ROLL_AUTHOR, src_dir],
        cwd=src_dir,
        stdout=api.raw_io.output()).stdout
  except api.step.StepFailure as f:
    output = f.result.stdout
    # Suppress failure for "refusing to roll backwards."
    if not re.search(REGEXP_ROLL_TOO_OLD, output):
      error = f

  match = re.search(REGEXP_ISSUE_CREATED, output)
  if match:
    issue = match.group('issue')
    file_contents = HTML_CONTENT % (ISSUE_URL_TEMPLATE % {'issue': issue})
    api.file.write('write %s' % FILENAME_CURRENT_ATTEMPT,
                   FILENAME_CURRENT_ATTEMPT,
                   file_contents)
    api.gsutil.upload(FILENAME_CURRENT_ATTEMPT,
                      global_constants.GS_GM_BUCKET,
                      FILENAME_CURRENT_ATTEMPT,
                      args=['-a', 'public-read'])

  roll_status = None
  for regexp, status_msg in ROLL_STATUSES:
    match = re.search(regexp, output)
    if match:
      roll_status = status_msg % match.groupdict()
      break

  if roll_status:
    api.file.write('write %s' % FILENAME_ROLL_STATUS,
                   FILENAME_ROLL_STATUS,
                   roll_status)
    api.gsutil.upload(FILENAME_ROLL_STATUS,
                      global_constants.GS_GM_BUCKET,
                      FILENAME_ROLL_STATUS,
                      args=['-a', 'public-read'])

  if error:
    # Pylint complains about raising NoneType, but that's exactly what we're
    # NOT doing here...
    # pylint: disable=E0702
    raise error


def GenTests(api):
  yield (
    api.test('AutoRoll_upload') +
    api.step_data('do auto_roll', retcode=0, stdout=api.raw_io.output(
        'Issue created. URL: https://codereview.chromium.org/1234'))
  )
  yield (
    api.test('AutoRoll_failed') +
    api.step_data('do auto_roll', retcode=1, stdout=api.raw_io.output('fail'))
  )
