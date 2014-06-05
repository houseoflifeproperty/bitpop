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
import Queue
import re
import signal
import smtplib
import socket
import subprocess
import sys
import threading
import urllib
import urllib2
from xml.dom import minidom

VERBOSE = True
EMAIL_ENABLED = False
BLINK_REVISIONS_URL = 'https://blink-status.appspot.com'
CHROMIUM_REVISIONS_URL = 'https://chromium-status.appspot.com'
CHROMIUM_LKCR_URL = 'https://build.chromium.org/p/chromium/lkcr-status'
V8_REVISIONS_URL = 'https://v8-status.appspot.com'
WEBRTC_REVISIONS_URL = 'https://webrtc-status.appspot.com'
REVISIONS_PASSWORD_FILE = '.status_password'

CHROMIUM_SVN_URL = 'svn://svn.chromium.org/chrome'
V8_SVN_URL = 'http://v8.googlecode.com/svn/branches/bleeding_edge'
WEBRTC_SVN_URL = 'http://webrtc.googlecode.com/svn/'

MASTER_TO_BASE_URL = {
  'chromium': 'http://build.chromium.org/p/chromium',
  'chromium.chrome': 'http://build.chromium.org/p/chromium.chrome',
  'chromium.linux': 'http://build.chromium.org/p/chromium.linux',
  'chromium.mac': 'http://build.chromium.org/p/chromium.mac',
  'chromium.win': 'http://build.chromium.org/p/chromium.win',
  'chromium.webkit': 'http://build.chromium.org/p/chromium.webkit',
  'client.v8': 'http://build.chromium.org/p/client.v8',
  'client.webrtc': 'http://build.chromium.org/p/client.webrtc',
}
RUN_LOG = []
UNKNOWN, SUCCESS, FAILURE, INPROGRESS = range(4)
GIT_HASH_RE = re.compile('^[a-fA-F0-9]{40}$')

# *_LKGR_STEPS controls which steps must pass for a revision to be marked
# as LKGR.
#-------------------------------------------------------------------------------

CHROMIUM_LKGR_STEPS = {
  'chromium.win': {
    'Win Builder (dbg)': [
      'compile',
    ],
    'Win7 Tests (dbg)(1)': [
      'ash_unittests',
      'aura_unittests',
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'check_deps',
      'chromedriver_unittests',
      'components_unittests',
      'compositor_unittests',
      'content_unittests',
      'courgette_unittests',
      'crypto_unittests',
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
      'url_unittests',
      'views_unittests',
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
  },  # chromium.win
  'chromium.mac': {
    'Mac Builder (dbg)': [
      'compile',
    ],
    'Mac 10.6 Tests (dbg)(1)': [
      'browser_tests',
      'cc_unittests',
      'chromedriver_unittests',
      'jingle_unittests',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'url_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    'Mac 10.6 Tests (dbg)(2)': [
      'browser_tests',
      'media_unittests',
      'net_unittests',
    ],
    'Mac 10.6 Tests (dbg)(3)': [
      'base_unittests', 'browser_tests', 'interactive_ui_tests',
    ],
    'Mac 10.6 Tests (dbg)(4)': [
      'browser_tests',
      'components_unittests',
      'content_unittests',
      'ipc_tests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
    ],
    'iOS Device': [
      'compile',
    ],
    'iOS Simulator (dbg)': [
      'compile',
      'base_unittests',
      'content_unittests',
      'crypto_unittests',
      'net_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'url_unittests',
    ],
  },  # chromium.mac
  'chromium.linux': {
    'Linux Builder (dbg)': [
      'compile',
    ],
    'Linux Builder (dbg)(32)': [
      'compile',
    ],
    'Linux Builder': [
      'checkdeps',
    ],
    'Linux Tests (dbg)(1)(32)': [
      'browser_tests',
      'content_browsertests',
      'net_unittests',
    ],
    'Linux Tests (dbg)(2)(32)': [
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'chromedriver_unittests',
      'components_unittests',
      'content_unittests',
      'crypto_unittests',
      'dbus_unittests',
      'device_unittests',
      'gpu_unittests',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle_unittests',
      'media_unittests',
      'nacl_integration',
      'ppapi_unittests',
      'printing_unittests',
      'remoting_unittests',
      'sandbox_linux_unittests',
      'sql_unittests',
      'sync_unit_tests',
      'ui_unittests',
      'unit_tests',
      'url_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    'Linux Tests (dbg)(1)': [
      'browser_tests',
      'net_unittests',
    ],
    'Linux Tests (dbg)(2)': [
      'base_unittests',
      'cacheinvalidation_unittests',
      'cc_unittests',
      'chromedriver_unittests',
      'components_unittests',
      'content_unittests',
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
      'url_unittests',
      'webkit_compositor_bindings_unittests',
    ],
    'Android Builder (dbg)': [
      'slave_steps',
    ],
    'Android Tests (dbg)': [
      'slave_steps',
    ],
    'Android Builder': [
      'slave_steps',
    ],
    'Android Tests': [
      'slave_steps',
    ],
    'Android Clang Builder (dbg)': [
      'slave_steps',
    ],
  },  # chromium.linux
  'chromium.chrome': {
    'Google Chrome Linux x64': [  # cycle time is ~14 mins as of 5/5/2012
      'compile',
    ],
  },  # chromium.chrome
}

# Last Known Compilable (Cool) Revision
CHROMIUM_LKCR_STEPS = {
  'chromium.win': {
    'Win Builder': [
      'compile',
      'runhooks',
      'update',
    ],
    'Win Builder (dbg)': [
      'compile',
      'runhooks',
      'update',
    ],
    'Win x64 Builder': [
      'compile',
      'runhooks',
      'update',
    ],
    'Win x64 Builder (dbg)': [
      'compile',
      'runhooks',
      'update',
    ],
  },  # chromium.win
  'chromium.mac': {
    'Mac Builder': [
      'bot_update',
      'compile',
      'gclient runhooks',
    ],
    'Mac Builder (dbg)': [
      'bot_update',
      'compile',
      'gclient runhooks',
    ],
  },  # chromium.mac
  'chromium.linux': {
    'Linux Builder': [
      'compile',
      'gclient runhooks',
    ],
    'Linux Builder (dbg)': [
      'compile',
      'gclient runhooks',
    ],
    'Linux Builder (dbg)(32)': [
      'compile',
      'gclient runhooks',
    ],
    'Linux Clang (dbg)': [
      'bot_update',
      'compile',
      'gclient runhooks',
    ],
    'Android Builder (dbg)': [
      'compile',
      'runhooks',
      'update',
    ],
    'Android Builder': [
      'compile',
      'runhooks',
      'update',
    ],
    'Android Clang Builder (dbg)': [
      'compile',
      'runhooks',
      'update',
    ],
  },  # chromium.linux
}

# For blink, for the moment, we only want to test bots that also exist
# in upstream variants. This helps us ensure that we won't pull a Chromium
# rev that is broken. The newest Chromium rev that isn't broken should also
# likely contain the newest revision of Blink that has been rolled downstream.
# This is still likely behind Blink HEAD by quite a bit, but at least is
# better than the Chromium LKGR.

BLINK_LKGR_STEPS = {
  'chromium.linux': {
    'Linux Builder (dbg)': ['compile'],
    'Linux Builder (dbg)(32)': ['compile'],
    'Android Builder (dbg)': ['slave_steps'],
    'Android Builder': ['slave_steps'],
  },
  'chromium.mac': {
    'Mac Builder (dbg)': ['compile'],
    },
  'chromium.win': {
    'Win Builder (dbg)': ['compile'],
  },
  'chromium.webkit': {
    'WebKit Win Builder (deps)': ['compile'],
    'WebKit Mac Builder (deps)': ['compile'],
    'WebKit Linux (deps)': ['compile'],
  },
}

V8_NORMAL_STEPS = ['compile', 'Check', 'Test262', 'Mozilla']

V8_CHECK = ['compile', 'Check']

V8_TEST262 = ['compile', 'Test262']

V8_GC = ['Mjsunit', 'Webkit']

V8_LKGR_STEPS = {
  'client.v8': {
    'V8 Linux - builder': ['compile'],
    'V8 Linux - debug builder': ['compile'],
    'V8 Linux - nosnap builder': ['compile'],
    'V8 Linux - nosnap debug builder': ['compile'],
    'V8 Linux': [
      'Check',
      'OptimizeForSize',
      'Test262',
      'Mozilla',
      'Presubmit',
      'Static-Initializers',
      'Webkit',
    ],
    'V8 Linux - debug': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - shared': V8_NORMAL_STEPS,
    'V8 Linux64 - builder': ['compile'],
    'V8 Linux64 - debug builder': ['compile'],
    'V8 Linux64': ['Check', 'OptimizeForSize', 'Test262', 'Mozilla',
                   'Static-Initializers'],
    'V8 Linux64 - debug': ['Check', 'Webkit', 'Test262', 'Mozilla'],
    'V8 Linux64 ASAN': ['Check'],
    'V8 Linux - nosnap': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - nosnap - debug': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - isolates': ['Check'],
    'V8 Linux - debug - isolates': ['Check'],
    'V8 Linux - nosse2': ['Check', 'Test262', 'Mozilla', 'GCMole'],
    'V8 Linux - debug - nosse2': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - nosse3': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - debug - nosse3': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - nosse4': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - debug - nosse4': ['Check', 'Test262', 'Mozilla'],
    'V8 Linux - deadcode': ['Check', 'Test262', 'Mozilla'],
    # TODO(machenbach): Disabled until enough slaves are available.
    # 'V8 Linux - interpreted regexp': V8_CHECK,
    'V8 Win32 - builder': ['compile'],
    'V8 Win32 - 1': ['Check', 'Test262', 'Mozilla', 'Webkit'],
    'V8 Win32 - 2': ['Check', 'Test262', 'Mozilla', 'Webkit'],
    'V8 Win32 - nosnap - shared': ['compile', 'Check'],
    'V8 Win32 - debug builder': ['compile'],
    'V8 Win32 - debug - 1': ['Check', 'Webkit', 'Test262', 'Mozilla'],
    'V8 Win32 - debug - 2': ['Check', 'Webkit', 'Test262', 'Mozilla'],
    'V8 Win32 - debug - 3': ['Check', 'Webkit', 'Test262', 'Mozilla'],
    'V8 Win64': V8_NORMAL_STEPS,
    'V8 Mac': V8_NORMAL_STEPS + ['Webkit'],
    'V8 Mac - debug': V8_CHECK + ['Webkit', 'Test262', 'Mozilla'],
    'V8 Mac64': V8_NORMAL_STEPS + ['Webkit'],
    'V8 Mac64 - debug': V8_CHECK + ['Webkit', 'Test262', 'Mozilla'],
    'V8 Arm - builder': ['compile'],
    'V8 Arm': V8_CHECK + ['OptimizeForSize', 'Webkit'],
    'V8 Arm - debug': V8_CHECK + ['OptimizeForSize', 'Webkit'],
    'V8 Linux - arm - sim': V8_CHECK + ['Test262', 'Mozilla'],
    'V8 Linux - arm - sim - debug': V8_CHECK + ['Test262', 'Mozilla'],
    'V8 Linux - arm64 - sim': V8_CHECK + ['Webkit', 'Test262', 'Mozilla'],
    'V8 GC Stress - 1': V8_GC,
    'V8 GC Stress - 2': V8_GC,
    'V8 GC Stress - 3': V8_GC,
    'Linux Debug Builder': ['compile'],
    'Linux ASAN Builder': ['compile'],
    'Android Builder': ['compile'],
    # TODO(machenbach): Disabled until there are pure builders available for
    # this. With a perf BuilderTester, the total lkgr cycle time is too big.
    # 'Chrome Win7 Perf': ['compile'],
    # 'Chrome Mac10.6 Perf': ['compile'],
    # 'Chrome Linux Perf': ['compile'],
    # TODO(machenbach): Disabled until stability issues with the windows bot
    # are resolved.
    # 'Webkit': ['compile'],
    'Webkit Mac': ['compile'],
    'Webkit Linux': ['compile'],
    'Webkit Linux 64': ['compile'],
    'Webkit Linux - dbg': ['compile'],
  },
}

WEBRTC_NORMAL_STEPS = [
    'compile',
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
    'modules_tests',
    'modules_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'video_engine_tests',
    'voice_engine_unittests',
]

WEBRTC_LKGR_STEPS = {
  'client.webrtc': {
    'Win32 Debug': WEBRTC_NORMAL_STEPS,
    'Win32 Release': WEBRTC_NORMAL_STEPS,
    'Win32 Release [large tests]': [
      'audio_device_tests',
      'video_capture_tests',
      'vie_auto_test',
      'voe_auto_test',
    ],
    'Win64 Debug': WEBRTC_NORMAL_STEPS,
    'Win64 Release': WEBRTC_NORMAL_STEPS,
    'Mac32 Debug': WEBRTC_NORMAL_STEPS,
    'Mac32 Release': WEBRTC_NORMAL_STEPS,
    'Mac32 Release [large tests]': [
      'audio_device_tests',
      'video_capture_tests',
      'vie_auto_test',
      'voe_auto_test',
    ],
    'Mac64 Debug': WEBRTC_NORMAL_STEPS,
    'Mac64 Release': WEBRTC_NORMAL_STEPS,
    'Mac Asan': WEBRTC_NORMAL_STEPS,
    'iOS Debug': ['compile'],
    'iOS Release': ['compile'],
    'Linux32 Debug': WEBRTC_NORMAL_STEPS,
    'Linux32 Release': WEBRTC_NORMAL_STEPS,
    'Linux64 Debug': WEBRTC_NORMAL_STEPS,
    'Linux64 Release': WEBRTC_NORMAL_STEPS,
    'Linux64 Release [large tests]': [
      'audio_e2e_test',
      'audioproc_perf',
      'isac_fixed_perf',
      'libjingle_peerconnection_java_unittest',
      'video_capture_tests',
      'vie_auto_test',
      'voe_auto_test',
    ],
    'Linux Clang': WEBRTC_NORMAL_STEPS,
    'Android': ['compile'],
    'Android (dbg)': ['compile'],
    'Android Clang (dbg)': ['compile'],
    'Chrome OS': WEBRTC_NORMAL_STEPS,
  },
}

#-------------------------------------------------------------------------------

class StatusGenerator(object):
  def master_cb(self, master):
    pass
  def builder_cb(self, builder):
    pass
  def revision_cb(self, revision):
    pass
  def build_cb(self, master, builder, status, build_num=None):
    pass
  def lkgr_cb(self, revision):
    pass


class HTMLStatusGenerator(StatusGenerator):
  def __init__(self, revisions, revcmp):  # pylint: disable=W0231
    self.masters = []
    self.rows = []
    self.blink_revisions = []
    self.revcmp = revcmp
    self.blink_rev_thread = threading.Thread(
        target=self._get_blink_revisions, args=(revisions[0], revcmp))
    self.blink_rev_thread.start()

  def _get_blink_revisions(self, since_revision, revcmp):
    deps_url = 'https://src.chromium.org/svn/trunk/src/DEPS'
    new_rev_regexp = re.compile('[+].*"webkit_revision": "([0-9]*)"')
    old_rev_regexp = re.compile('[-].*"webkit_revision": "([0-9]*)"')
    cmd = ['svn', 'log', '--xml', '-r', '%s:HEAD' % since_revision,
           deps_url]
    subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    doc = [None]
    def _parser_main():
      doc[0] = minidom.parse(subproc.stdout)
    parser_thread = threading.Thread(target=_parser_main)
    parser_thread.start()
    subproc.wait()
    parser_thread.join()
    jobq = Queue.Queue()
    result = []
    for logentry in doc[0].childNodes[0].getElementsByTagName('logentry'):
      jobq.put(logentry.getAttribute('revision'))

    def _diff_main():
      while True:
        try:
          job = jobq.get_nowait()
        except Queue.Empty:
          return
        log_cmd = ['svn', 'diff', '-c', job, deps_url]
        grep_cmd = ['grep', '-e', '^[+-].*"webkit_revision": "[0-9]*"']
        log_proc = subprocess.Popen(log_cmd, stdout=subprocess.PIPE)
        grep_proc = subprocess.Popen(grep_cmd, stdin=log_proc.stdout,
                                     stdout=subprocess.PIPE)
        (grep_out, _) = grep_proc.communicate()
        log_proc.wait()
        if grep_out:
          m_new = re.search(new_rev_regexp, grep_out)
          m_old = re.search(old_rev_regexp, grep_out)
          if m_new:
            result.append(
                (job, m_new.group(1), m_old.group(1) if m_old else None))

    # pylint: disable=W0612
    log_threads = [threading.Thread(target=_diff_main) for i in range(10)]
    for t in log_threads:
      t.start()
    for t in log_threads:
      t.join()
    self.blink_revisions = sorted(result, key=lambda x: x[0], cmp=revcmp)

  def master_cb(self, master):
    self.masters.append((master, []))

  def builder_cb(self, builder):
    self.masters[-1][1].append(builder)

  def revision_cb(self, revision):
    tmpl = 'https://src.chromium.org/viewvc/chrome?view=rev&revision=%s'
    row = [
        revision,
        '<td class="revision"><a href="%s" target="_blank">%s</a></td>\n' % (
            tmpl % urllib.quote(revision), revision)]
    self.rows.append(row)

  def build_cb(self, master, builder, status, build_num=None):
    stat_txt = ['unknown', 'success', 'failure', 'inprogress'][status]
    cell = '  <td class="%s">' % stat_txt
    if build_num is not None:
      build_url = 'build.chromium.org/p/%s/builders/%s/builds/%s' % (
          master, builder, build_num)
      cell += '<a href="http://%s" target="_blank">X</a>' % (
          urllib.quote(build_url))
    cell += '</td>\n'
    self.rows[-1].append(cell)

  def lkgr_cb(self, revision):
    row = self.rows[-1]
    row[1] = row[1].replace('class="revision"', 'class="lkgr"', 1)
    for i in range(2, len(row)):
      row[i] = row[i].replace('class="success"', 'class="lkgr"', 1)

  def generate(self):
    if self.blink_rev_thread:
      self.blink_rev_thread.join(120)
    if self.blink_rev_thread.isAlive():
      blinkrevs = [(-1, '?', '?')]
    else:
      blinkrevs = list(self.blink_revisions)
    html_chunks = ["""
<html>
<head>
<style type="text/css">
table { border-collapse: collapse; }
th { font-size: xx-small; }
td, th { text-align: center; }
.header { border: 1px solid black; }
.revision { padding-left: 5px; padding-right: 5px; }
.revision { border-left: 1px solid black; border-right: 1px solid black; }
.success { background-color: #8d4; }
.failure { background-color: #e88; }
.inprogress { background-color: #fe1; }
.unknown { background-color: #ddd; }
.lkgr { background-color: #4af; }
.roll { border-top: 2px solid black; }
</style>
</head>
<body><table>
"""]
    master_headers = ['<tr class="header"><th></th><th></th>\n']
    builder_headers = ['<tr class="header">']
    builder_headers.append('<th>blink revision</th>\n')
    builder_headers.append('<th>chromium revision</th>\n')
    for master, builders in self.masters:
      master_url = 'build.chromium.org/p/%s' % master
      hdr = '  <th colspan="%d" class="header">' % len(builders)
      hdr += '<a href="%s" target="_blank">%s</a></th>\n' % (
          'http://%s' % urllib.quote(master_url), master)
      master_headers.append(hdr)
      for builder in builders:
        builder_url = 'build.chromium.org/p/%s/builders/%s' % (
            master, builder)
        hdr = '  <th><a href="%s" target="_blank">%s</a></th>\n' % (
            'http://%s' % urllib.quote(builder_url), builder)
        builder_headers.append(hdr)
    master_headers.append('</tr>\n')
    builder_headers.append('</tr>\n')
    html_chunks.extend(master_headers)
    html_chunks.extend(builder_headers)
    blink_tmpl = 'https://src.chromium.org/viewvc/blink?view=rev&revision=%s'
    blinkrev = blinkrevs[-1][1]
    for row in self.rows:
      rowclass = ''
      while blinkrevs and self.revcmp(row[0], blinkrevs[-1][0]) < 0:
        rowclass = ' class="roll"'
        blinkrev = blinkrevs[-1][2] or '?'
        blinkrevs.pop()
        if blinkrevs:
          blinkrev = blinkrevs[-1][1]
      html_chunks.append('<tr%s><td class="revision">' % rowclass)
      html_chunks.append('<a href="%s">%s</a></td>' % (
          blink_tmpl % blinkrev, blinkrev))
      html_chunks.extend(row[1:])
      html_chunks.append('</tr>\n')
    html_chunks.append('</table></body></html>\n')
    return ''.join(html_chunks)


def SendMail(sender, recipients, subject, message):
  if not EMAIL_ENABLED:
    return
  try:
    body = ['From: %s' % sender]
    body.append('To: %s' % recipients)
    body.append('Subject: %s' % subject)
    # Default to sending replies to the recipient list, not the account running
    # the script, since that's probably just a role account.
    body.append('Reply-To: %s' % recipients)
    body.append('')
    body.append(message)
    server = smtplib.SMTP('localhost')
    server.sendmail(sender, recipients.split(','), '\n'.join(body))
    server.quit()
  except Exception as e:
    # If smtp fails, just dump the output. If running under cron, that will
    # capture the output and send its own (ugly, but better than nothing) email.
    print message
    print ('\n--------- Exception in %s -----------\n' %
           os.path.basename(__file__))
    raise e

def FormatPrint(s):
  return '%s: %s' % (datetime.datetime.now(), s)

def Print(s):
  msg = FormatPrint(s)
  RUN_LOG.append(msg)
  print msg

def VerbosePrint(s):
  if VERBOSE:
    Print(s)
  else:
    RUN_LOG.append(FormatPrint(s))

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
    # Note that builds will be modified concurrently by multiple threads.
    # That's safe for simple modifications like this, but don't iterate builds.
    builds[builder] = builder_history
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % url)

def FetchLKGR(revisions_url):
  lkgr_url = '%s/lkgr' % revisions_url
  try:
    # pylint: disable=E1121
    url_fh = urllib2.urlopen(lkgr_url, None, 60)
  except urllib2.URLError:
    VerbosePrint('URLException while fetching %s' % lkgr_url)
    return
  try:
     # TODO: Fix for git: git revisions can't be converted to int.
    return int(url_fh.read())
  finally:
    url_fh.close()

def FetchBuildData(lkgr_steps):
  builds = dict((master, {}) for master in MASTER_TO_BASE_URL)
  fetch_threads = []
  for master, builders in lkgr_steps.iteritems():
    for builder in builders:
      th = threading.Thread(target=FetchBuildsMain,
                            name='Fetch %s' % builder,
                            args=(master, builder, builds[master]))
      th.start()
      fetch_threads.append(th)
  for th in fetch_threads:
    th.join()

  return builds

def ReadBuildData(fn):
  try:
    if fn == '-':
      fn = '<stdin>'
      return json.load(sys.stdin)
    else:
      with open(fn, 'r') as fh:
        return json.load(fh)
  except Exception, e:
    sys.stderr.write('Could not read build data from %s:\n%s\n' % (
        fn, repr(e)))
    raise

def SvnRevisionCheck(r):
  try:
    r = int(r)
  except (TypeError, ValueError):
    return False
  return r > 0

def SvnRevisionCmp(a, b):
  return cmp(int(a), int(b))

def GitRevisionCheck(r):
  return bool(GIT_HASH_RE.match(r))

def GitRevisionCmp(a, b):
  raise RuntimeError('git revision comparison is unimplemented.')

def EvaluateBuildData(build_data, builder_lkgr_steps):
  step_data = {}
  reasons = []
  status = SUCCESS
  for step in build_data['steps']:
    step_data[step['name']] = step
  for lkgr_step in builder_lkgr_steps:
    # This allows us to rename a step and tell lkgr_finder that it should
    # accept either name for step status.  We assume in the code that any
    # given build will have at most one of the two steps.
    if isinstance(lkgr_step, str):
      steps = (lkgr_step,)
    else:
      steps = lkgr_step
    matching_steps = [s for s in step_data if s in steps]
    if not matching_steps:
      reasons.append('Step %s is not listed on the build.' % (lkgr_step,))
    elif len(matching_steps) > 1:
      reasons.append('Multiple step matches: %s' % matching_steps)
      status = FAILURE
      continue
    else:
      step = matching_steps[0]
      cur_data = step_data[step]
      if (cur_data.get('isFinished') is True and 'results' in cur_data):
        result_data = cur_data['results'][0]
        if type(result_data) == list:
          result_data = result_data[0]
        if result_data and str(result_data) not in ('0', '1'):
          reasons.append('Step %s failed' % step)
          status = FAILURE
        continue
      else:
        reasons.append('Step %s has not completed (isFinished: %s)' % (
            step, step_data[step].get('isFinished')))
    if build_data['currentStep'] is not None and status != FAILURE:
      status = INPROGRESS
    else:
      status = FAILURE
  return status, reasons

def CollateRevisionHistory(build_data, lkgr_steps, revcheck, revcmp):
  """
  Organize builder data into:
    build_history = {master: {builder: [(revision, bool, build_num), ...]}}
    revisions = [revision, ...]
  ... with revisions and build_history[master][builder] sorted by revcmp.

  Args:
    build_data: json-formatted build data returned by buildbot.
    lkgr_steps: List of interesting builders and steps.
    revcheck: Predicate function which checks the sanity of the 'revision'
        field in build_data.
    revcmp: Comparator function for sorting builds by 'revision'
  """
  build_history = {}
  revisions = set()
  for master, master_data in build_data.iteritems():
    if master not in lkgr_steps:
      continue
    master_history = build_history.setdefault(master, {})
    for (builder, builder_data) in master_data.iteritems():
      if builder not in lkgr_steps[master]:
        continue
      builder_history = []
      for build_num in sorted(builder_data.keys(), key=int):
        this_build_data = builder_data[build_num]
        txt = this_build_data.get('text', [])
        if 'exception' in txt and 'slave' in txt and 'lost' in txt:
          continue
        revision = None
        for prop in this_build_data.get('properties', []):
          if prop[0] == 'got_revision':
            revision = prop[1]
            break
        if not revision:
          revision = this_build_data.get(
              'sourceStamp', {}).get('revision', None)
        if not revision or not revcheck(revision):
          continue
        revisions.add(str(revision))
        status, _ = EvaluateBuildData(
            this_build_data, lkgr_steps[master][builder])
        builder_history.append((revision, status, build_num))
      master_history[builder] = sorted(
          builder_history, key=lambda x: x[0], cmp=revcmp)
  revisions = sorted(revisions, cmp=revcmp)
  # Sanity check; buildbot data sometimes has bogus old revisions
  first_good_rev = 0
  while int(revisions[-1]) - int(revisions[first_good_rev]) > 10000:
    first_good_rev += 1
  return (build_history, revisions[first_good_rev:])

def FindLKGRCandidate(build_history, revisions, revcmp, status_gen=None):
  """Given a build_history of builds, run the algorithm for finding an LKGR
  candidate (refer to the algorithm description at the top of this script).
  green1 and green2 record the sequence of two successful builds that are
  required for LKGR.
  """
  lkgr = None
  if not status_gen:
    status_gen = StatusGenerator()
  builders = []
  for master, master_history in build_history.iteritems():
    status_gen.master_cb(master)
    for builder, builder_history in master_history.iteritems():
      status_gen.builder_cb(builder)
      gen = reversed(builder_history)
      prev = []
      try:
        prev.append(gen.next())
      except StopIteration:
        prev.append((-1, UNKNOWN, -1))
      builders.append((master, builder, gen, prev))
  for revision in reversed(revisions):
    status_gen.revision_cb(revision)
    good_revision = True
    for master, builder, gen, prev in builders:
      try:
        while revcmp(revision, prev[-1][0]) < 0:
          prev.append(gen.next())
      except StopIteration:
        prev.append((-1, UNKNOWN, -1))

      # current build matches revision
      if revcmp(revision, prev[-1][0]) == 0:
        status = prev[-1][1]
      elif len(prev) == 1:
        assert revcmp(revision, prev[-1][0]) > 0
        # most recent build is behind revision
        status = UNKNOWN
      elif prev[-1][1] == UNKNOWN:
        status = UNKNOWN
      else:
        # We color space between FAILED and INPROGRESS builds as FAILED,
        # since that is what it will eventually become.
        if prev[-1][1] == SUCCESS and prev[-2][1] == INPROGRESS:
          status = INPROGRESS
        elif prev[-1][1] == prev[-2][1] == SUCCESS:
          status = SUCCESS
        else:
          status = FAILURE
      build_num = prev[-1][2] if revcmp(revision, prev[-1][0]) == 0 else None
      status_gen.build_cb(master, builder, status, build_num)
      if status != SUCCESS:
        good_revision = False
    if not lkgr and good_revision:
      lkgr = revision
      status_gen.lkgr_cb(revision)
  return lkgr

def PostLKGR(revisions_url, lkgr, password_file, dry):
  url = '%s/revisions' % revisions_url
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

def CheckLKGRLag(lag_age, rev_gap, allowed_lag_hrs, allowed_rev_gap):
  """Determine if the LKGR lag is acceptable for current commit activity.

    Returns True if the lag is within acceptable thresholds.
  """
  # Lag isn't an absolute threshold because when things are slow, e.g. nights
  # and weekends, there could be bad revisions that don't get noticed and
  # fixed right away, so LKGR could go a long time without updating, but it
  # wouldn't be a big concern, so we want to back off the 'ideal' threshold.
  # When the tree is active, we don't want to back off much, or at all, to keep
  # the lag under control.

  if rev_gap == 0:
    return True

  lag_hrs = (lag_age.days * 24) + (lag_age.seconds / 3600)
  if not lag_hrs:
    return True

  rev_rate = rev_gap / lag_hrs

  # This causes the allowed_lag to back off proportionally to how far LKGR is
  # below the gap threshold, roughly throttled by the rate of commits since the
  # last LKGR.
  # Equation arbitrarily chosen to fit the range of 2 to 22 hours when using the
  # default allowed_lag and allowed_gap. Might need tweaking.
  max_lag_hrs = ((1 + max(0, allowed_rev_gap - rev_gap) /
                  min(30, max(15, rev_rate))) * allowed_lag_hrs)

  VerbosePrint('LKGR is %s hours old (threshold: %s hours)' %
               (lag_hrs, max_lag_hrs))

  return lag_age < datetime.timedelta(hours=max_lag_hrs)

def GetLKGRAge(lkgr, repo):
  """Parse the LKGR revision timestamp from the svn log."""
  lkgr_age = datetime.timedelta(0)
  cmd = ['svn', 'log', '--non-interactive', '--xml', '-r', str(lkgr), repo]
  process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
  stdout = process.communicate()[0]
  if not process.returncode:
    match = re.search('<date>(?P<dt>.*)</date>', stdout)
    if match:
      lkgr_dt = datetime.datetime.strptime(match.group('dt'),
                                           '%Y-%m-%dT%H:%M:%S.%fZ')
      lkgr_age = datetime.datetime.utcnow() - lkgr_dt
  return lkgr_age


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
  opt_parser.add_option('--write-to-file',
                        help='Write new LKGR to FILE', metavar='FILE')
  opt_parser.add_option('--password-file', default=REVISIONS_PASSWORD_FILE,
                        dest='pwfile', metavar='FILE',
                        help='File containing password for chromium-status app')
  opt_parser.add_option('--notify', default=[],
                        action='append', metavar='HOST:PORT',
                        help='Notify this master when a new LKGR is found')
  opt_parser.add_option('--manual', help='Set LKGR manually')
  opt_parser.add_option('--build-data', metavar='FILE', dest='build_data',
                        help='Rather than querying the build master, read the '
                        'build data from this file.  Passing "-" as the '
                        'argument will read from stdin.')
  opt_parser.add_option('--dump-build-data', metavar='FILE', dest='dump_file',
                        help='For debugging, dump the raw json build data.')
  opt_parser.add_option('--email-errors', action='store_true', default=False,
                        help='Send e-mail to LKGR admins on errors (for cron).')
  opt_parser.add_option('--allowed-gap', type='int', default=150,
                        help='How many revisions to allow between head and '
                        'LKGR before it\'s considered out-of-date.')
  opt_parser.add_option('--allowed-lag', type='int', default=2,
                        help='How long (in hours) since an LKGR update before'
                        'it\'s considered out-of-date. This is a minimum and '
                        'will be increased when commit activity slows.')
  opt_parser.add_option('--html', metavar='FILE',
                        help='Output details in HTML format '
                             '(for troubleshooting LKGR staleness issues).')
  opt_parser.add_option('-b', '--blink', action='store_true', default=False,
                        help='Find the Blink LKGR rather than the Chromium '
                             'one.')
  opt_parser.add_option('--v8', action='store_true', default=False,
                        help='Find the V8 LKGR rather than the Chromium one.')
  opt_parser.add_option('--chromium-lkcr', action='store_true', default=False,
                        help='Find the Chromium LKCR instead of LKGR.')
  opt_parser.add_option('-w', '--webrtc', action='store_true', default=False,
                        help='Find the WebRTC LKGR rather than the Chromium '
                             'one.')
  opt_parser.add_option('--error-recipients',
                        default='chrome-troopers+alerts@google.com',
                        help='Send email to the specified recipients '
                             'when errors occur (default %default).')
  opt_parser.add_option('--update-recipients',
                        default=None,
                        help='Send email to the specified recipients '
                             'when updating LKGR (default %default).')
  options, args = opt_parser.parse_args()

  if sum([options.blink,
          options.v8,
          options.chromium_lkcr,
          options.webrtc]) > 1:
    opt_parser.error('You can only specify one of --blink, --v8, '
                     '--chromium-lkcr or --webrtc '
                     'in the same run.')

  # Error notification setup.
  fqdn = socket.getfqdn()
  sender = '%s@%s' % (os.environ.get('LOGNAME', 'unknown'), fqdn)
  error_recipients = options.error_recipients
  update_recipients = options.update_recipients
  subject_base = os.path.basename(__file__) + ': '

  global EMAIL_ENABLED
  EMAIL_ENABLED = options.email_errors

  if args:
    opt_parser.print_usage()
    SendMail(sender, error_recipients, subject_base + 'Usage error',
             ' '.join(sys.argv) + '\n' + opt_parser.get_usage())
    return 1

  global VERBOSE
  VERBOSE = not options.quiet

  if options.blink:
    lkgr_type = 'Blink'
    revisions_url = BLINK_REVISIONS_URL
    lkgr_steps = BLINK_LKGR_STEPS
    svn_url = CHROMIUM_SVN_URL
  elif options.v8:
    lkgr_type = 'V8'
    revisions_url = V8_REVISIONS_URL
    lkgr_steps = V8_LKGR_STEPS
    svn_url = V8_SVN_URL
  elif options.webrtc:
    lkgr_type = 'WebRTC'
    revisions_url = WEBRTC_REVISIONS_URL
    lkgr_steps = WEBRTC_LKGR_STEPS
    svn_url = WEBRTC_SVN_URL
  elif options.chromium_lkcr:
    lkgr_type = 'ChromiumLKCR'
    revisions_url = CHROMIUM_LKCR_URL
    lkgr_steps = CHROMIUM_LKCR_STEPS
    svn_url = CHROMIUM_SVN_URL
  else:
    lkgr_type = 'Chromium'
    revisions_url = CHROMIUM_REVISIONS_URL
    lkgr_steps = CHROMIUM_LKGR_STEPS
    svn_url = CHROMIUM_SVN_URL

  if options.manual:
    PostLKGR(revisions_url, options.manual, options.pwfile, options.dry)
    for master in options.notify:
      NotifyMaster(master, options.manual, options.dry)
      if update_recipients:
        subject = 'Updated %s LKGR to %s (manually)' % (
            lkgr_type, options.manual)
        message = subject + '.\n'
        SendMail(sender, update_recipients, subject, message)
    return 0

  lkgr = FetchLKGR(revisions_url)
  if lkgr is None:
    SendMail(sender, error_recipients, subject_base +
             'Failed to fetch %s LKGR' % lkgr_type, '\n'.join(RUN_LOG))
    return 1

  if options.build_data:
    builds = ReadBuildData(options.build_data)
  else:
    builds = FetchBuildData(lkgr_steps)

  if options.dump_file:
    try:
      with open(options.dump_file, 'w') as fh:
        json.dump(builds, fh, indent=2)
    except IOError, e:
      sys.stderr.write('Could not dump to %s:\n%s\n' % (
          options.dump_file, repr(e)))

  # TODO: Fix this for git
  revcheck = SvnRevisionCheck
  revcmp = SvnRevisionCmp

  (build_history, revisions) = CollateRevisionHistory(
      builds, lkgr_steps, revcheck, revcmp)
  status_gen = None
  if options.html:
    status_gen = HTMLStatusGenerator(revisions, revcmp)
  candidate = FindLKGRCandidate(build_history, revisions, revcmp, status_gen)
  if options.html:
    fh = open(options.html, 'w')
    fh.write(status_gen.generate())
    fh.close()

  VerbosePrint('-' * 52)
  VerbosePrint('Current %s LKGR is %d' % (lkgr_type, lkgr))
  VerbosePrint('-' * 52)
  # TODO: Fix for git
  if candidate and int(candidate) > lkgr:
    VerbosePrint('Candidate %s LKGR is %s' % (lkgr_type, candidate))
    for master in lkgr_steps.keys():
      formdata = ['builder=%s' % urllib2.quote(x)
                  for x in lkgr_steps[master].keys()]
      formdata = '&'.join(formdata)
      waterfall = '%s?%s' % (MASTER_TO_BASE_URL[master] + '/console', formdata)
      VerbosePrint('%s Waterfall URL:' % master)
      VerbosePrint(waterfall)
    if options.post:
      PostLKGR(revisions_url, candidate, options.pwfile, options.dry)
      if update_recipients:
        subject = 'Updated %s LKGR to %s' % (lkgr_type, candidate)
        message = subject + '.\n'
        SendMail(sender, update_recipients, subject, message)

    if options.write_to_file and not options.dry:
      with open(options.write_to_file, 'w') as f:
        f.write('%s' % candidate)

    for master in options.notify:
      NotifyMaster(master, candidate, options.dry)
  else:
    VerbosePrint('No newer %s LKGR found than current %s' % (lkgr_type, lkgr))
    rev_behind = int(revisions[-1]) - lkgr
    VerbosePrint('%s LKGR is behind by %s revisions' % (lkgr_type, rev_behind))
    if options.html:
      # Make sure there is whitespace between the link below and the next line,
      # to avoid e.g. gmail using the timestamp from the following line
      # as the link target.
      VerbosePrint('See LKGR status at http://build.chromium.org/p/chromium/lkgr-status/ .')
    if rev_behind > options.allowed_gap:
      SendMail(sender, error_recipients,
               '%s%s LKGR (%s) > %s revisions behind' %
               (subject_base, lkgr_type, lkgr, options.allowed_gap),
               '\n'.join(RUN_LOG))
      return 1

    if not CheckLKGRLag(GetLKGRAge(lkgr, svn_url), rev_behind,
                        options.allowed_lag,
                        options.allowed_gap):
      SendMail(sender, error_recipients,
               '%s%s LKGR (%s) exceeds lag threshold' %
               (subject_base, lkgr_type, lkgr), '\n'.join(RUN_LOG))
      return 1

  VerbosePrint('-' * 52)

  return 0

if __name__ == '__main__':
  sys.exit(main())
