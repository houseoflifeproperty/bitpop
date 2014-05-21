#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Fetch the latest results for a pre-selected set of builders we care about.
If we find a 'good' revision -- based on criteria explained below -- we
mark the revision as LKGR, and POST it to the LKGR server:

http://chromium-status.appspot.com/lkgr

We're looking for a sequence in the revision history that looks something
like this:

  Revision        Builder1        Builder2        Builder3
 -----------------------------------------------------------
     12357         green

     12355                                         green

     12352                         green

     12349                                         green

     12345         green


Given this revision history, we mark 12352 as LKGR.  Why?

  - We know 12352 is good for Builder2.
  - Since Builder1 had two green builds in a row, we can be reasonably
    confident that all revisions between the two builds (12346 - 12356,
    including 12352), are also green for Builder1.
  - Same reasoning for Builder3.

To find a revision that meets these criteria, we can walk backward through
the revision history until we get a green build for every builder.  When
that happens, we mark a revision as *possibly* LKGR.  We then continue
backward looking for a second green build on all builders (and no failures).
For all builders that are green on the LKGR candidate itself (12352 in the
example), that revision counts as BOTH the first and second green builds.
Hence, in the example above, we don't look for an actual second green build
of Builder2.

Note that this arrangement is symmetrical; we could also walk forward through
the revisions and run the same algorithm.  Since we are only interested in the
*latest* good revision, we start with the most recent revision and walk
backward.
"""

# The 2 following modules are not present on python 2.5
# pylint: disable=F0401
import datetime
import json
import multiprocessing
import optparse
import os
import signal
import sys
import threading
import urllib
import urllib2


VERBOSE = True

REVISIONS_URL = 'https://chromium-status.appspot.com'
REVISIONS_PASSWORD_FILE = '.status_password'
MASTER_TO_BASE_URL = {
  'chromium': 'http://build.chromium.org/p/chromium',
  'chromium.chrome': 'http://build.chromium.org/p/chromium.chrome',
  'chromium.linux': 'http://build.chromium.org/p/chromium.linux',
  'chromium.mac': 'http://build.chromium.org/p/chromium.mac',
  'chromium.win': 'http://build.chromium.org/p/chromium.win',
}

# LKGR_STEPS controls which steps must pass for a revision to be marked
# as LKGR.
#-------------------------------------------------------------------------------

LKGR_STEPS = {
  'chromium.win': {
    'Win Builder (dbg)': [
      'compile',
    ],
    'Win7 Tests (dbg)(1)': [
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'check_deps',
      'chromedriver2_unittests',
      'content_unittests',
      'courgette_unittests',
      'crypto_unittests',
      'googleurl_unittests',
      'installer_util_unittests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'webkit_compositor_bindings_unittests',
    ],
    'Win7 Tests (dbg)(2)': [
      'net_unittests', 'browser_tests',
    ],
    'Win7 Tests (dbg)(3)': [
      'browser_tests',
    ],
    'Win7 Tests (dbg)(4)': [
      'browser_tests',
    ],
    'Win7 Tests (dbg)(5)': [
      'browser_tests',
    ],
    'Win7 Tests (dbg)(6)': [
      'browser_tests',
    ],
    'Chrome Frame Tests (ie8)': [
      'chrome_frame_unittests',
    ],
    # 'Interactive Tests (dbg)': [
    #   'interactive_ui_tests',
    # ],
    'Win Aura': [
      'ash_unittests',
      'aura_unittests',
      'browser_tests',
      'compile',
      'compositor_unittests',
      'content_browsertests',
      'content_unittests',
      'interactive_ui_tests',
      'unit_tests',
      'views_unittests',
    ],
  },  # chromium.win
  'chromium.mac': {
    'Mac Builder (dbg)': [
      'compile',
    ],
    'Mac 10.6 Tests (dbg)(1)': [
      'browser_tests',
      'cc_unittests',
      'chromedriver2_unittests',
      'googleurl_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'jingle_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    'Mac 10.6 Tests (dbg)(2)': [
      'browser_tests',
      'check_deps',
      'media_unittests',
      'net_unittests',
    ],
    'Mac 10.6 Tests (dbg)(3)': [
      'base_unittests', 'browser_tests', 'interactive_ui_tests',
    ],
    'Mac 10.6 Tests (dbg)(4)': [
      'browser_tests',
      'content_unittests',
      'ipc_tests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
    ],
  },  # chromium.mac
  'chromium.linux': {
    'Linux Builder (dbg)': [
      'compile',
    ],
    'Linux Builder x64': [
      'check_deps',
    ],
    'Linux Tests (dbg)(1)': [
      'browser_tests',
      'net_unittests',
    ],
    'Linux Tests (dbg)(2)': [
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'chromedriver2_unittests',
      'content_unittests',
      'googleurl_unittests',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'nacl_integration',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'webkit_compositor_bindings_unittests',
    ],
    'Linux Aura': [
      'aura_unittests',
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'compile',
      'compositor_unittests',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'device_unittests',
      'googleurl_unittests',
      'gpu_unittests',
      'ipc_tests',
      'interactive_ui_tests',
      'jingle_unittests',
      'media_unittests',
      'net_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'views_unittests',
    ],
    'Android Builder (dbg)': [
      'build',
    ],
    'Android Tests (dbg)': [
      'build',
    ],
    'Android Clang Builder (dbg)': [
      'build',
    ],
  },  # chromium.linux
  'chromium.chrome': {
    'Google Chrome Linux x64': [  # cycle time is ~14 mins as of 5/5/2012
      'compile',
    ],
  },  # chromium.chrome
}

#-------------------------------------------------------------------------------

def Print(s):
  print '%s: %s' % (datetime.datetime.now(), s)

def VerbosePrint(s):
  if VERBOSE:
    Print(s)

def FetchBuildsMain(master, builder, builds):
  if master not in MASTER_TO_BASE_URL:
    raise Exception('ERROR: master %s not in MASTER_TO_BASE_URL' % master)
  master_url = MASTER_TO_BASE_URL[master]
  url = '%s/json/builders/%s/builds/_all' % (master_url, urllib2.quote(builder))
  try:
    # Requires python 2.6
    # pylint: disable=E1121
    url_fh = urllib2.urlopen(url, None, 600)
    builder_history = json.load(url_fh)
    url_fh.close()
    # check_deps was moved to Linux Builder x64 at build 39789.  Ignore
    # builds older than that.
    if builder == 'Linux Builder x64':
      for build in builder_history.keys():
        if int(build) < 39789:
          Print('removing build %s from Linux Build x64' % build)
          del builder_history[build]
    builds[master][builder] = builder_history
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % url)

def CollateRevisionHistory(builds, lkgr_steps):
  """Organize builder data into:
  build_history = [ (revision, {master: {builder: True/False, ...}, ...}), ... ]
  ... and sort revisions chronologically, latest revision first
  """
  # revision_history[revision][builder] = True/False (success/failure)
  revision_history = {}
  for master in builds.keys():
    for (builder, builder_history) in builds[master].iteritems():
      VerbosePrint('%s/%s:' % (master, builder))
      for (build_num, build_data) in builder_history.iteritems():
        build_num = int(build_num)
        revision = build_data['sourceStamp']['revision']
        if not revision:
          continue
        steps = {}
        reasons = []
        for step in build_data['steps']:
          steps[step['name']] = step
        for step in lkgr_steps[master][builder]:
          if step not in steps:
            reasons.append('Step %s has not completed.' % step)
            continue
          if ('isFinished' not in steps[step] or
             steps[step]['isFinished'] is not True):
            reasons.append('Step %s has not completed (%s)' % (
                step, steps[step]['isFinished']))
            continue
          if 'results' in steps[step]:
            result = steps[step]['results'][0]
            if type(result) == list:
              result = result[0]
            if result and str(result) not in ('0', '1'):
              reasons.append('Step %s failed' % step)
        revision_history.setdefault(revision, {})
        revision_history[revision].setdefault(master, {})
        if reasons:
          revision_history[revision][master][builder] = False
          VerbosePrint('  Build %s (rev %s) is bad or incomplete' % (
              build_num, revision))
          for reason in reasons:
            VerbosePrint('    %s' % reason)
        else:
          revision_history[revision][master][builder] = True

  # Need to fix the sort for git
  # pylint: disable=W0108
  sorted_keys = sorted(revision_history.keys(), None, lambda x: int(x), True)
  build_history = [(rev, revision_history[rev]) for rev in sorted_keys]

  return build_history

def FindLKGRCandidate(build_history, lkgr_steps):
  """Given a build_history of builds, run the algorithm for finding an LKGR
  candidate (refer to the algorithm description at the top of this script).
  green1 and green2 record the sequence of two successful builds that are
  required for LKGR.
  """
  candidate = -1
  green1 = {}
  green2 = {}
  num_builders = 0
  for master in lkgr_steps.keys():
    num_builders += len(lkgr_steps[master])

  for entry in build_history:
    if len(green2) == num_builders:
      break
    revision = entry[0]
    history = entry[1]
    if candidate == -1:
      master_loop_must_break = False
      for master in history.keys():
        if master_loop_must_break:
          break
        for (builder, status) in history[master].iteritems():
          if not status:
            candidate = -1
            green1.clear()
            master_loop_must_break = True
            break
          green1[master + '/' + builder] = revision
      if len(green1) == num_builders:
        candidate = revision
        for master in history.keys():
          for builder in history[master].keys():
            green2[master + '/' + builder] = revision
      continue
    master_loop_must_break = False
    for master in history.keys():
      if master_loop_must_break:
        break
      for (builder, status) in history[master].iteritems():
        if not status:
          candidate = -1
          green1.clear()
          green2.clear()
          master_loop_must_break = True
          break
        green2[master + '/' + builder] = revision

  if candidate != -1 and len(green2) == num_builders:
    VerbosePrint('-' * 80)
    VerbosePrint('Revision %s is good based on:' % candidate)
    revlist = list(green2.iteritems())
    revlist.sort(None, lambda x: x[1])
    for (builder, revision) in revlist:
      VerbosePrint('  Revision %s is green for builder %s' %
                   (revision, builder))
    VerbosePrint('-' * 80)
    revlist = list(green1.iteritems())
    revlist.sort(None, lambda x: x[1])
    for (builder, revision) in revlist:
      VerbosePrint('  Revision %s is green for builder %s' %
                   (revision, builder))
    return candidate

  return -1

def PostLKGR(lkgr, password_file, dry):
  url = '%s/revisions' % REVISIONS_URL
  VerbosePrint('Posting to %s...' % url)
  try:
    password_fh = open(password_file, 'r')
    password = password_fh.read().strip()
    password_fh.close()
  except IOError:
    Print('Could not read password file %s' % password_file)
    Print('Aborting upload')
    return
  params = {
    'revision': lkgr,
    'success': 1,
    'password': password
  }
  params = urllib.urlencode(params)
  Print(params)
  if not dry:
    # Requires python 2.6
    # pylint: disable=E1121
    request = urllib2.urlopen(url, params)
    request.close()
  VerbosePrint('Done!')

def NotifyMaster(master, lkgr, dry=False):
  def _NotifyMain():
    sys.argv = [
        'buildbot', 'sendchange',
        '--master', master,
        '--revision', lkgr,
        '--branch', 'src',
        '--who', 'lkgr',
        '--category', 'lkgr',
        'no file information']
    if dry:
      return
    import buildbot.scripts.runner
    buildbot.scripts.runner.run()

  p = multiprocessing.Process(None, _NotifyMain, 'notify-%s' % master)
  p.start()
  p.join(5)
  if p.is_alive():
    Print('Timeout while notifying %s' % master)
    # p.terminate() can hang; just obliterate the sucker.
    os.kill(p.pid, signal.SIGKILL)

def main():
  opt_parser = optparse.OptionParser()
  opt_parser.add_option('-q', '--quiet', default=False,
                        dest='quiet', action='store_true',
                        help='Suppress verbose output to stdout')
  opt_parser.add_option('-n', '--dry-run', default=False,
                        dest='dry', action='store_true',
                        help="Don't actually upload new LKGR")
  opt_parser.add_option('--post', default=False,
                        dest='post', action='store_true',
                        help='Upload new LKGR to chromium-status app')
  opt_parser.add_option('--password-file', default=REVISIONS_PASSWORD_FILE,
                        dest='pwfile', metavar='FILE',
                        help='File containing password for chromium-status app')
  opt_parser.add_option('--notify', default=[],
                        action='append', metavar='HOST:PORT',
                        help='Notify this master when a new LKGR is found')
  opt_parser.add_option('--manual', help='Set LKGR manually')
  options, args = opt_parser.parse_args()

  if args:
    opt_parser.print_usage()
    sys.exit(1)

  global VERBOSE
  VERBOSE = not options.quiet

  if options.manual:
    PostLKGR(options.manual, options.pwfile, options.dry)
    for master in options.notify:
      NotifyMaster(master, options.manual, options.dry)
    return 0

  builds = {}
  # Prime builds with the dictionaries it will need per master.
  for master in MASTER_TO_BASE_URL.keys():
    builds.setdefault(master, {})
  fetch_threads = []
  lkgr = -1

  for master in LKGR_STEPS.keys():
    for builder in LKGR_STEPS[master].keys():
      th = threading.Thread(target=FetchBuildsMain,
                            name='Fetch %s' % builder,
                            args=(master, builder, builds))
      th.start()
      fetch_threads.append(th)

  lkgr_url = '%s/lkgr' % REVISIONS_URL
  try:
    # Requires python 2.6
    # pylint: disable=E1121
    url_fh = urllib2.urlopen(lkgr_url, None, 60)
    # Fix for git
    lkgr = int(url_fh.read())
    url_fh.close()
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % lkgr_url)
    return 1

  for th in fetch_threads:
    th.join()

  build_history = CollateRevisionHistory(builds, LKGR_STEPS)
  candidate = FindLKGRCandidate(build_history, LKGR_STEPS)

  VerbosePrint('-' * 80)
  VerbosePrint('LKGR=%d' % lkgr)
  VerbosePrint('-' * 80)
  # Fix for git
  if candidate != -1 and int(candidate) > lkgr:
    VerbosePrint('Revision %s is new LKGR' % candidate)
    for master in LKGR_STEPS.keys():
      formdata = ['builder=%s' % urllib2.quote(x)
                  for x in LKGR_STEPS[master].keys()]
      formdata = '&'.join(formdata)
      waterfall = '%s?%s' % (MASTER_TO_BASE_URL[master] + '/console', formdata)
      VerbosePrint('%s Waterfall URL:' % master)
      VerbosePrint(waterfall)
    if options.post:
      PostLKGR(candidate, options.pwfile, options.dry)
    for master in options.notify:
      NotifyMaster(master, candidate, options.dry)
  else:
    VerbosePrint('No newer LKGR found than current %s' % lkgr)
  VerbosePrint('-' * 80)

  return 0

if __name__ == '__main__':
  sys.exit(main())
