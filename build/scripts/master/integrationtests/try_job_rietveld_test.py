#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""try_job_rietveld.py integration testcases.

   These represent checks using the live data providers and other
   components external to the source, and thus not unit testable.
"""

import os
import sys
import unittest
from twisted.internet import reactor
from twisted.python import log

import test_env  # pylint: disable=W0611

from master import try_job_rietveld

# pylint: disable=W0212
users = try_job_rietveld._ValidUserPoller(None)

# We shouldn't have known failures in the long run, but this way
# the test will start by passing.
known_missing_users = [
    'idana', 'jhaas', 'jon', 'lzheng', 'nickbaum', 'niranjan', 'tigerf',
    ]

class ValidUserTest(unittest.TestCase):

  # These names exist elsewhere is source, and will cause issues if invalid.
  def test_cq_name(self):
    self.assertTrue(users.contains('commit-bot@chromium.org'))
    self.assertTrue(users.contains('chromeos-lkgm@google.com'))

  # These are hard-coded base names to provide useful bootstrap
  # sanity checks.  Of course if these people cease to be
  # comitters, these should be replaced, just like OWNERS files.
  def test_common_user_names(self):
    self.assertTrue(users.contains('jam@chromium.org'))
    self.assertTrue(users.contains('maruel@chromium.org'))

  def test_author(self):
    self.assertTrue(users.contains('petermayo@chromium.org'))

  def test_nonuser_names(self):
    self.assertFalse(users.contains(''))
    # Hopefully nobody will pick this as a chromium userid.
    self.assertFalse(users.contains('nasty'))
    self.assertFalse(users.contains('chromium.org'))
    self.assertFalse(users.contains('google.com'))

  def test_all_committers(self):
    committers_file = 'committers.txt'
    known_failures = set(known_missing_users)
    msg = ('We need the committers from the CQ copied or linked to %s' %
           committers_file)
    self.assertTrue(os.path.isfile(committers_file), msg)
    missing_committers = [
      user for user in (email.strip()
          for email in open(committers_file).readlines())
            if user and not users.contains(user + users._NORMAL_DOMAIN) and
              not user in known_failures]
    self.assertEqual(
        missing_committers, [],
        'CQ user(s) who can not run try jobs : %r' % missing_committers)


def poll_and_stop():
  d = users._poll()
  d.addCallback(lambda _x, _y: reactor.stop())
  d.addErrback(lambda _: reactor.stop())
  return d

def setup():
  log.startLogging(sys.stderr)
  reactor.callLater(0, poll_and_stop)
  reactor.run()

def pretest():
  update_me = False
  for problem in known_missing_users:
    if users.contains(problem + users._NORMAL_DOMAIN):
      log.msg('%s does not still seem to be a problem' % problem)
      update_me = True
  if update_me:
    log.msg('Please get this test updated.')

if __name__ == '__main__':
  setup()
  pretest()
  unittest.main()
