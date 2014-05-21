#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for pending_manager.py."""

import logging
import os
import re
import sys
import time
import traceback
import unittest
import urllib2

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

import find_depot_tools  # pylint: disable=W0611
import breakpad

import context
import pending_manager
from verification import base
from verification import fake
from verification import project_base
from verification import reviewer_lgtm

# In tests/
import mocks


def read(filename):
  f = open(filename, 'rb')
  content = f.read()
  f.close()
  return content


def write(filename, content):
  f = open(filename, 'wb')
  f.write(content)
  f.close()


def trim(x):
  return x.replace(' ', '').replace('\n', '')


def _try_comment(issue=31337):
  return (
      "add_comment(%d, u'%shttp://localhost/author@example.com/%d/1\\n')" %
      (issue, pending_manager.PendingManager.TRYING_PATCH.replace('\n', '\\n'),
        issue))


class TestPendingManager(mocks.TestCase):
  def setUp(self):
    super(TestPendingManager, self).setUp()
    self.root_dir = ROOT_DIR

  def testLoadSave(self):
    pc = pending_manager.PendingManager(
        context.Context(None, None, mocks.AsyncPushMock(self)),
        [fake.FakeVerifier(base.SUCCEEDED)],
        [])
    filename = os.path.join(self.root_dir, 'foo.json')
    empty = """{
  "__persistent_type__": "PendingQueue",
  "pending_commits": []
}
"""
    write(filename, empty)
    try:
      pc.load(filename)
      self.assertEquals(pc.queue.pending_commits, [])
      pc.save(filename)
      self.assertEquals(trim(empty), trim(read(filename)))
    finally:
      os.remove(filename)
      if os.path.exists(filename + '.old'):
        os.remove(filename + '.old')

  def _get_pc(self, verifiers_no_patch, verifiers):
    return pending_manager.PendingManager(
        self.context, verifiers_no_patch, verifiers)

  def _check_standard_verification(self, pc, success, defered):
    """Verifies the checkout and rietveld calls."""
    pc.scan_results()
    self.assertEquals(len(pc.queue.pending_commits), 0)
    if pc.verifiers:
      if success:
        self.context.checkout.check_calls(
            [ 'prepare(None)',
              'apply_patch(%r)' % (self.context.rietveld.patchsets[0],),
              'prepare(None)',  # Will sync to HEAD/124.
              'apply_patch(%r)' % (self.context.rietveld.patchsets[1],),
              "commit(u'foo\\n\\nReview URL: http://nowhere/31337', "
                "u'author@example.com')"])
        self.context.rietveld.check_calls(
            [ _try_comment(),
              'close_issue(31337)',
              "update_description(31337, u'foo')",
              "add_comment(31337, 'Change committed as 125')"])
      else:
        self.context.checkout.check_calls(
            [ 'prepare(None)',
              'apply_patch(%r)' % (self.context.rietveld.patchsets[0],)])
        self.context.rietveld.check_calls(
            [ _try_comment(),
              "set_flag(31337, 1, 'commit', 'False')",
              "add_comment(31337, %r)" % pc.FAILED_NO_MESSAGE])
    else:
      if success:
        self.context.checkout.check_calls(
          self._prepare_apply_commit(0, 31337))
        self.context.rietveld.check_calls(
            [ _try_comment(),
              'close_issue(31337)',
              "update_description(31337, u'foo')",
              "add_comment(31337, 'Change committed as 125')"])
      else:
        # checkout is never touched in that case.
        self.context.checkout.check_calls([])
        if defered:
          self.context.rietveld.check_calls(
              [ _try_comment(),
                "set_flag(31337, 1, 'commit', 'False')",
                "add_comment(31337, %r)" % pc.FAILED_NO_MESSAGE])
        else:
          self.context.rietveld.check_calls(
              [ "set_flag(31337, 1, 'commit', 'False')",
                "add_comment(31337, %r)" % pc.FAILED_NO_MESSAGE])

  def _prepare_apply_commit(self, index, issue):
    """Returns a frequent sequence of action happening on the Checkout object.

    The list returned by this function should be used as an argument to
    self.context.checkout.check_calls().
    """
    return [
      # Reverts any previous modification or checkout the tree if it was not
      # present.
      'prepare(None)',
      # Applies the requested PatchSet.
      'apply_patch(%r)' % self.context.rietveld.patchsets[index],
      # Commits the patch.
      "commit(u'foo\\n\\nReview URL: http://nowhere/%d', "
        "u'author@example.com')" % issue,
    ]

  def testNoVerification(self):
    try:
      # Need at least one verification.
      self._get_pc([], [])
      self.fail()
    except AssertionError:
      pass
    try:
      # Cannot have the same verifier two times.
      self._get_pc(
          [fake.FakeVerifier(base.SUCCEEDED)],
          [fake.FakeVerifier(base.SUCCEEDED)])
      self.fail()
    except AssertionError:
      pass

  def _check_1(self, pc, result):
    # 'initial' won't be sent if the pre-patch verification fails, this is to
    # not add noise for ignored CLs.
    send_initial_packet = (result == base.SUCCEEDED or pc.verifiers)
    self.assertEquals(len(pc.queue.pending_commits), 0)
    pc.look_for_new_pending_commit()
    self.assertEquals(len(pc.queue.pending_commits), 1)
    commit = pc.queue.pending_commits[0]
    self.assertEquals(len(commit.verifications), 0)
    pc.process_new_pending_commit()
    if result == base.FAILED:
      self.assertEquals([], pc.queue.pending_commits)
    else:
      commit = pc.queue.pending_commits[0]
      self.assertEquals(commit.verifications['fake'].get_state(), result)
      self.assertEquals(len(commit.verifications), 1)
    pc.update_status()
    if result == base.FAILED:
      self.assertEquals([], pc.queue.pending_commits)
    else:
      commit = pc.queue.pending_commits[0]
      self.assertEquals(commit.verifications['fake'].get_state(), result)
      self.assertEquals('', commit.relpath)
      self.assertEquals(len(commit.verifications), 1)
    self._check_standard_verification(pc, result == base.SUCCEEDED, False)

    if result == base.SUCCEEDED:
      self.context.status.check_names(['initial', 'commit'])
    elif send_initial_packet:
      self.context.status.check_names(['initial', 'abort'])
    else:
      # Only happens when there is no verifier that requires a patch.
      self.context.status.check_names(['abort'])

  def testNoPatchVerification(self):
    pc = self._get_pc([fake.FakeVerifier(base.SUCCEEDED)], [])
    self._check_1(pc, base.SUCCEEDED)

  def testPatchVerification(self):
    pc = self._get_pc([], [fake.FakeVerifier(base.SUCCEEDED)])
    self._check_1(pc, base.SUCCEEDED)

  def testNoPatchVerificationFail(self):
    pc = self._get_pc([fake.FakeVerifier(base.FAILED)], [])
    self._check_1(pc, base.FAILED)

  def testPatchVerificationFail(self):
    pc = self._get_pc([], [fake.FakeVerifier(base.FAILED)])
    self._check_1(pc, base.FAILED)

  def testPatchDiscardThrows(self):
    # Handle HTTPError correctly.
    result = []
    pc = self._get_pc([], [fake.FakeVerifier(base.FAILED)])

    def set_flag_throw(_issue, _patchset, _flag, _value):
      raise urllib2.HTTPError(None, None, None, None, None)

    def send_stack(*_args, **_kwargs):
      result.append(True)

    self.mock(breakpad, 'SendStack', send_stack)
    self.mock(traceback, 'print_stack', lambda: None)
    self.mock(logging, 'error', lambda _: None)
    pc.context.rietveld.set_flag = set_flag_throw

    self.assertEquals(len(pc.queue.pending_commits), 0)
    pc.look_for_new_pending_commit()
    self.assertEquals(len(pc.queue.pending_commits), 1)
    commit = pc.queue.pending_commits[0]
    self.assertEquals(len(commit.verifications), 0)
    pc.process_new_pending_commit()
    self.assertEquals([], pc.queue.pending_commits)
    pc.update_status()
    self.assertEquals([], pc.queue.pending_commits)
    self.context.checkout.check_calls(
        [ 'prepare(None)',
          'apply_patch(%r)' % (self.context.rietveld.patchsets[0],),
        ])
    self.context.rietveld.check_calls(
        [ _try_comment(),
          "add_comment(31337, %r)" % pc.FAILED_NO_MESSAGE,
        ])
    self.context.status.check_names(['initial', 'abort'])

  def _check_defer_1(self, pc, result):
    self.assertEquals(len(pc.queue.pending_commits), 0)
    pc.look_for_new_pending_commit()
    self.assertEquals(len(pc.queue.pending_commits), 1)
    commit = pc.queue.pending_commits[0]
    self.assertEquals(len(commit.verifications), 0)
    pc.process_new_pending_commit()
    commit = pc.queue.pending_commits[0]
    self.assertEquals('', commit.relpath)
    self.assertEquals(commit.verifications['fake'].get_state(), base.PROCESSING)
    self.assertEquals(len(commit.verifications), 1)
    pc.update_status()
    commit = pc.queue.pending_commits[0]
    self.assertEquals('', commit.relpath)
    self.assertEquals(commit.verifications['fake'].get_state(), result)
    self.assertEquals(len(commit.verifications), 1)
    self._check_standard_verification(pc, result == base.SUCCEEDED, True)
    if result == base.SUCCEEDED:
      self.context.status.check_names(['initial', 'commit'])
    else:
      self.context.status.check_names(['initial', 'abort'])

  def testDeferNoPatchVerification(self):
    pc = self._get_pc([fake.DeferredFakeVerifier(base.SUCCEEDED)], [])
    self._check_defer_1(pc, base.SUCCEEDED)

  def testDeferPatchVerification(self):
    pc = self._get_pc([], [fake.DeferredFakeVerifier(base.SUCCEEDED)])
    self._check_defer_1(pc, base.SUCCEEDED)

  def testDeferNoPatchVerificationFail(self):
    pc = self._get_pc([fake.DeferredFakeVerifier(base.FAILED)], [])
    self._check_defer_1(pc, base.FAILED)

  def testDeferPatchVerificationFail(self):
    pc = self._get_pc([], [fake.DeferredFakeVerifier(base.FAILED)])
    self._check_defer_1(pc, base.FAILED)

  def _check_4(self, f1, f2, f3, f4):
    fake1 = fake.FakeVerifier(f1)
    fake1.name = 'fake1'
    fake2 = fake.FakeVerifier(f2)
    fake2.name = 'fake2'
    fake3 = fake.FakeVerifier(f3)
    fake3.name = 'fake3'
    fake4 = fake.FakeVerifier(f4)
    fake4.name = 'fake4'
    nb = 1
    if f1 is base.SUCCEEDED:
      nb = 2
      if f2 is base.SUCCEEDED:
        nb = 3
        if f3 is base.SUCCEEDED:
          nb = 4
    pc = self._get_pc([fake1, fake2], [fake3, fake4])
    self.assertEquals(len(pc.queue.pending_commits), 0)
    pc.look_for_new_pending_commit()
    self.assertEquals(len(pc.queue.pending_commits), 1)
    commit = pc.queue.pending_commits[0]
    self.assertEquals(len(commit.verifications), 0)
    pc.process_new_pending_commit()
    if not all(f == base.SUCCEEDED for f in (f1, f2, f3, f4)):
      self.assertEquals([], pc.queue.pending_commits)
    else:
      commit = pc.queue.pending_commits[0]
      self.assertEquals(commit.verifications['fake1'].get_state(), f1)
      self.assertEquals(commit.verifications['fake2'].get_state(), f2)
      self.assertEquals(commit.verifications['fake3'].get_state(), f3)
      self.assertEquals(commit.verifications['fake4'].get_state(), f4)
      self.assertEquals(len(commit.verifications), nb)
    pc.update_status()
    if not all(f == base.SUCCEEDED for f in (f1, f2, f3, f4)):
      self.assertEquals([], pc.queue.pending_commits)
    else:
      commit = pc.queue.pending_commits[0]
      self.assertEquals(commit.verifications['fake1'].get_state(), f1)
      self.assertEquals(commit.verifications['fake2'].get_state(), f2)
      self.assertEquals(commit.verifications['fake3'].get_state(), f3)
      self.assertEquals(commit.verifications['fake4'].get_state(), f4)
      self.assertEquals(len(commit.verifications), nb)
    self._check_standard_verification(
        pc, all(x == base.SUCCEEDED for x in (f1, f2, f3, f4)), False)
    if all(x == base.SUCCEEDED for x in (f1, f2, f3, f4)):
      self.context.status.check_names(['initial', 'commit'])
    else:
      self.context.status.check_names(['initial', 'abort'])

  def test4thVerificationFail(self):
    self._check_4(base.SUCCEEDED, base.SUCCEEDED, base.SUCCEEDED, base.FAILED)

  def test4Verification(self):
    self._check_4(
        base.SUCCEEDED, base.SUCCEEDED, base.SUCCEEDED, base.SUCCEEDED)

  def test4Verification3rdFail(self):
    self._check_4(base.SUCCEEDED, base.SUCCEEDED, base.FAILED, base.SUCCEEDED)

  def _check_defer_4(self, f1, f2, f3, f4):
    fake1 = fake.DeferredFakeVerifier(f1)
    fake1.name = 'fake1'
    fake2 = fake.DeferredFakeVerifier(f2)
    fake2.name = 'fake2'
    fake3 = fake.DeferredFakeVerifier(f3)
    fake3.name = 'fake3'
    fake4 = fake.DeferredFakeVerifier(f4)
    fake4.name = 'fake4'
    pc = self._get_pc([fake1, fake2], [fake3, fake4])
    self.assertEquals(len(pc.queue.pending_commits), 0)
    pc.look_for_new_pending_commit()
    self.assertEquals(len(pc.queue.pending_commits), 1)
    commit = pc.queue.pending_commits[0]
    self.assertEquals(len(commit.verifications), 0)
    pc.process_new_pending_commit()
    commit = pc.queue.pending_commits[0]
    self.assertEquals(
        commit.verifications['fake1'].get_state(), base.PROCESSING)
    self.assertEquals(
        commit.verifications['fake2'].get_state(), base.PROCESSING)
    self.assertEquals(
        commit.verifications['fake3'].get_state(), base.PROCESSING)
    self.assertEquals(
        commit.verifications['fake4'].get_state(), base.PROCESSING)
    self.assertEquals(len(commit.verifications), 4)
    pc.update_status()
    self.assertEquals(commit.verifications['fake1'].get_state(), f1)
    self.assertEquals(commit.verifications['fake2'].get_state(), f2)
    self.assertEquals(commit.verifications['fake3'].get_state(), f3)
    self.assertEquals(commit.verifications['fake4'].get_state(), f4)
    self.assertEquals('', commit.relpath)
    self._check_standard_verification(
        pc, all(x == base.SUCCEEDED for x in (f1, f2, f3, f4)), False)
    if all(x == base.SUCCEEDED for x in (f1, f2, f3, f4)):
      self.context.status.check_names(['initial', 'commit'])
    else:
      self.context.status.check_names(['initial', 'abort'])

  def testDefer4thVerificationFail(self):
    self._check_defer_4(
        base.SUCCEEDED, base.SUCCEEDED, base.SUCCEEDED, base.FAILED)

  def testDefer4Verification(self):
    self._check_defer_4(
        base.SUCCEEDED, base.SUCCEEDED, base.SUCCEEDED, base.SUCCEEDED)

  def testDefer4Verification3rdFail(self):
    self._check_defer_4(
        base.SUCCEEDED, base.SUCCEEDED, base.FAILED, base.SUCCEEDED)

  def testRelPath(self):
    verifiers = [
        project_base.ProjectBaseUrlVerifier(
          [r'^%s(.*)$' % re.escape(r'http://example.com/')]),
    ]
    pc = self._get_pc([], verifiers)
    pc.context.rietveld.issues[31337]['base_url'] = 'http://example.com/sub/dir'
    pc.look_for_new_pending_commit()
    self.assertEquals(1, len(pc.queue.pending_commits))
    pc.process_new_pending_commit()
    self.assertEquals('sub/dir', pc.queue.pending_commits[0].relpath)
    self.context.checkout.check_calls(
        [ 'prepare(None)',
          'apply_patch(%r)' % (self.context.rietveld.patchsets[0],)])
    pc.update_status()
    self.context.checkout.check_calls([])
    pc.scan_results()
    self.context.checkout.check_calls(
        # Will sync to HEAD, 124.
        self._prepare_apply_commit(1, 31337))
    self.context.rietveld.check_calls(
        [ _try_comment(),
          'close_issue(31337)',
          "update_description(31337, u'foo')",
          "add_comment(31337, 'Change committed as 125')"])
    self.context.status.check_names(['initial', 'commit'])

  def testCommitBurst(self):
    pc = self._get_pc([fake.FakeVerifier(base.SUCCEEDED)], [])
    self.assertEquals(4, pc.MAX_COMMIT_BURST)
    timestamp = [1]
    self.mock(time, 'time', lambda: timestamp[-1])
    for i in range(pc.MAX_COMMIT_BURST + 2):
      self.context.rietveld.issues[i] = (
          self.context.rietveld.issues[31337].copy())
      self.context.rietveld.issues[i]['issue'] = i
    pc.look_for_new_pending_commit()
    self.assertEquals(len(pc.queue.pending_commits), pc.MAX_COMMIT_BURST + 3)
    pc.process_new_pending_commit()
    pc.update_status()
    pc.scan_results()
    self.context.checkout.check_calls(
        self._prepare_apply_commit(0, 0) +
        self._prepare_apply_commit(1, 1) +
        self._prepare_apply_commit(2, 2) +
        self._prepare_apply_commit(3, 3))
    self.context.rietveld.check_calls(
        [ _try_comment(0),
          _try_comment(1),
          _try_comment(2),
          _try_comment(3),
          _try_comment(4),
          _try_comment(5),
          _try_comment(),
          'close_issue(0)',
          "update_description(0, u'foo')",
          "add_comment(0, 'Change committed as 125')",
          'close_issue(1)',
          "update_description(1, u'foo')",
          "add_comment(1, 'Change committed as 125')",
          'close_issue(2)',
          "update_description(2, u'foo')",
          "add_comment(2, 'Change committed as 125')",
          'close_issue(3)',
          "update_description(3, u'foo')",
          "add_comment(3, 'Change committed as 125')",
        ])
    self.assertEquals(3, len(pc.queue.pending_commits))
    # Dry run.
    pc.scan_results()
    self.context.checkout.check_calls([])
    self.context.rietveld.check_calls([])
    # Remove one item from the burst.
    pc.recent_commit_timestamps.pop()
    pc.scan_results()
    next_item = pc.MAX_COMMIT_BURST
    self.context.checkout.check_calls(
        self._prepare_apply_commit(next_item, next_item))
    self.context.rietveld.check_calls(
        [ 'close_issue(%d)' % next_item,
          "update_description(%d, u'foo')" % next_item,
          "add_comment(%d, 'Change committed as 125')" % next_item,
        ])
    # After a delay, must flush the queue.
    timestamp.append(timestamp[-1] + pc.COMMIT_BURST_DELAY + 1)
    pc.scan_results()
    self.context.checkout.check_calls(
        self._prepare_apply_commit(next_item + 1, next_item + 1) +
        self._prepare_apply_commit(next_item + 2, 31337))
    self.context.rietveld.check_calls(
        [ 'close_issue(%d)' % (next_item + 1),
          "update_description(%d, u'foo')" % (next_item + 1),
          "add_comment(%d, 'Change committed as 125')" % (next_item + 1),
          'close_issue(31337)',
          "update_description(31337, u'foo')",
          "add_comment(31337, 'Change committed as 125')"])
    total = pc.MAX_COMMIT_BURST + 3
    self.context.status.check_names(['initial'] * total + ['commit'] * total)

  def testIgnored(self):
    verifiers = [
        project_base.ProjectBaseUrlVerifier(
          [r'^%s(.*)$' % re.escape(r'http://example.com/')]),
    ]
    pc = self._get_pc(verifiers, [])
    pc.context.rietveld.issues[31337]['base_url'] = 'http://unrelated.com/sub'
    pc.look_for_new_pending_commit()
    pc.process_new_pending_commit()
    pc.update_status()
    pc.scan_results()
    self.assertEquals(1, len(pc.queue.pending_commits))
    self.assertEquals('', pc.queue.pending_commits[0].relpath)
    self.assertEquals(base.IGNORED, pc.queue.pending_commits[0].get_state())

  def testDisapeared(self):
    verifiers = [
        project_base.ProjectBaseUrlVerifier(
          [r'^%s(.*)$' % re.escape(r'http://example.com/')]),
    ]
    pc = self._get_pc(verifiers, [])
    pc.context.rietveld.issues[31337]['base_url'] = 'http://unrelated.com/sub'
    pc.look_for_new_pending_commit()
    pc.process_new_pending_commit()
    pc.update_status()
    pc.scan_results()
    self.assertEquals(1, len(pc.queue.pending_commits))
    del pc.context.rietveld.issues[31337]
    pc.look_for_new_pending_commit()
    pc.process_new_pending_commit()
    pc.update_status()
    pc.scan_results()
    self.assertEquals(0, len(pc.queue.pending_commits))
    self.context.status.check_names(['abort'])

  def _get_pc_reviewer(self):
    verifiers = [
        reviewer_lgtm.ReviewerLgtmVerifier(
          ['.*'], [re.escape('commit-bot@example.com')])
    ]
    pc = self._get_pc(verifiers, [])
    return pc

  def _approve(self, sender=None):
    if not sender:
      sender = self.context.rietveld.issues[31337]['reviewers'][0]
    self.context.rietveld.issues[31337]['messages'].append(
        {
          'approval': True,
          'sender': sender,
        })

  def testVerifyDefaultMock(self):
    # Verify mock expectation for the default settings.
    pc = self._get_pc_reviewer()
    self.assertEquals(0, len(pc.queue.pending_commits))
    pc.look_for_new_pending_commit()
    self.assertEquals(1, len(pc.queue.pending_commits))
    pc.process_new_pending_commit()
    self.assertEquals(0, len(pc.queue.pending_commits))
    pc.update_status()
    self.assertEquals(0, len(pc.queue.pending_commits))
    self.context.rietveld.check_calls(
        [ "set_flag(31337, 1, 'commit', 'False')",
          "add_comment(31337, %r)" % reviewer_lgtm.LgtmStatus.NO_LGTM])
    self.context.status.check_names(['abort'])

  def testVerifyDefaultMockPlusLGTM(self):
    # Verify mock expectation with a single approval message.
    pc = self._get_pc_reviewer()
    self._approve()
    self.assertEquals(0, len(pc.queue.pending_commits))
    pc.look_for_new_pending_commit()
    self.assertEquals(1, len(pc.queue.pending_commits))
    pc.process_new_pending_commit()
    self.assertEquals(1, len(pc.queue.pending_commits))
    pc.update_status()
    self.assertEquals(1, len(pc.queue.pending_commits))
    pc.scan_results()
    self.assertEquals(0, len(pc.queue.pending_commits))
    self.context.rietveld.check_calls(
        [ _try_comment(),
          'close_issue(31337)',
          "update_description(31337, u'foo')",
          "add_comment(31337, 'Change committed as 125')"])
    self.context.status.check_names(['initial', 'commit'])
    self.context.checkout.check_calls(
        self._prepare_apply_commit(0, 31337))

  def testDriveBy(self):
    pc = self._get_pc_reviewer()
    self._approve()
    pc.look_for_new_pending_commit()
    pc.process_new_pending_commit()
    pc.update_status()
    # A new reviewer prevents the commit.
    i = self.context.rietveld.issues[31337]
    i['reviewers'] = i['reviewers'] + ['annoying@dude.org']
    pc.scan_results()
    self.context.rietveld.check_calls(
        [ _try_comment(),
          "set_flag(31337, 1, 'commit', 'False')",
          'add_comment(31337, "List of reviewers changed. annoying@dude.org '
              'did a drive-by without LGTM\'ing!")'])
    self.context.status.check_names(['initial', 'abort'])

  def testDriveByLGTM(self):
    pc = self._get_pc_reviewer()
    self._approve()
    pc.look_for_new_pending_commit()
    pc.process_new_pending_commit()
    pc.update_status()
    # He's nice, he left a LGTM.
    i = self.context.rietveld.issues[31337]
    i['reviewers'] = i['reviewers'] + ['nice@dude.org']
    self._approve('nice@dude.org')
    pc.scan_results()
    self.assertEquals(0, len(pc.queue.pending_commits))
    self.context.rietveld.check_calls(
        [ _try_comment(),
          'close_issue(31337)',
          "update_description(31337, u'foo')",
          "add_comment(31337, 'Change committed as 125')"])
    self.context.status.check_names(['initial', 'commit'])
    self.context.checkout.check_calls(
        self._prepare_apply_commit(0, 31337))


if __name__ == '__main__':
  logging.basicConfig(
      level=[logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][
        min(sys.argv.count('-v'), 3)],
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
