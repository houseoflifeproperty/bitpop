#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for common.gerrit's 'object.py'"""

import test_env  # pylint: disable=W0611
import unittest
from datetime import datetime

# Disable wildcard import warning | pylint: disable=W0401
from common.gerrit.object import GerritObject, LabelInfo, AccountInfo, \
    ApprovalInfo, ReviewInput, ChangeInfo, ChangeMessageInfo, RevisionInfo


class GerritObjectTestCase(unittest.TestCase):

  def testHash(self):
    g1 = GerritObject(key='value')
    g2 = GerritObject(key='value2')
    h1 = hash(g1)
    h2 = hash(g1)
    self.assertEqual(h1, h2)
    self.assertEqual(g1, g1)
    self.assertEqual(g2, g2)
    self.assertNotEquals(g1, g2)

  def testImmutable(self):
    go = GerritObject(key='value')
    self.assertEqual(go['key'], 'value')

    def assign():
      go['key2'] = 'fail'
    self.assertRaises(TypeError, assign)

  def testImmutableChildren(self):
    go = GerritObject(key={'inner_key':1})
    self.assertEqual(go['key']['inner_key'], 1)

    def assign():
      go['key']['inner_key'] = 2
    self.assertRaises(TypeError, assign)

  def testImmutableChildLists(self):
    go = GerritObject(key=[1, 2, 3])
    self.assertEqual(go['key'][1], 2)

    def assign():
      go['key'][2] = 10
    self.assertRaises(TypeError, assign)

  def testAssignment(self):
    GerritObject(key=1)
    GerritObject(key='hello')
    GerritObject(key={'1':1, '2':2})
    GerritObject(key=[1, 2, 3])
    GerritObject(key=(1, 2, 3))

    def assign():
      GerritObject(key={1:1})
    self.assertRaises(TypeError, assign)

  def testExtend(self):
    self.assertEqual(
        GerritObject(key='a', key2='b').extend().data,
        {'key': 'a', 'key2': 'b'})

    self.assertEqual(
        GerritObject(key='a', key2='b').extend(key2='c').data,
        {'key': 'a', 'key2': 'c'})

    self.assertEqual(
        GerritObject(key='a', key2='b').extend(key3='c').data,
        {'key': 'a', 'key2': 'b', 'key3': 'c'})

    self.assertEqual(
        GerritObject(key='a', key2='b').extend(
            **GerritObject(key2='c', key3='d')).data,
        {'key': 'a', 'key2': 'c', 'key3': 'd'})


class ChangeInfoTestCase(unittest.TestCase):

  def setUp(self):
    # Subset of a real 'ChangeInfo' for testing
    self.ci = ChangeInfo.fromJsonDict({
            'id': 'project~branch~12345~change',
            'change_id': 12345,
            'created': '2014-02-11 12:14:28.135200000',
            'updated': '2014-03-11 00:20:08.946000000',
            'current_revision': 'THIRD',
            'owner': {
                'name': 'Some Person',
            },
            'revisions': {
                'THIRD': {
                    '_number': 3,
                },
                'SECOND': {
                    '_number': 2,
                },
                'FIRST': {
                    '_number': 1,
                },
            },
            'labels': {
                'Test-Label': {
                    'approved': {},
                    'rejected': {},
                    },
                'Other-Label': {},
            },
        })
    self.msgci = self.ci.extend(
        messages=[
            {
                'id': 1,
                'author': 'test-user@test.org',
                'date': '2014-02-11 12:10:14.311200000',
                'message': 'MESSAGE1',
            },
            {
                'id': 2,
                'date': '2014-02-11 12:11:14.311200000',
                'message': 'MESSAGE2',
                '_revision_number': 2,
            },
        ],
    )
    self.empty = ChangeInfo.fromJsonDict({})

  @staticmethod
  def _buildRevisionInfo(change_info, revision_hash):
    return RevisionInfo(
        revision_hash,
        **change_info['revisions'][revision_hash])

  def testParseId(self):
    self.assertEqual(
        ChangeInfo.parse_id('a~b~c~d~e'),
        ('a', 'b', 'c~d~e'))

  def testIdTuple(self):
    self.assertEqual(
        self.ci.id_tuple,
        ('project', 'branch', '12345~change'))

  def testUniqueId(self):
    self.assertEqual(
        self.ci.unique_id,
        ('project~branch~12345~change', '2014-03-11 00:20:08.946000000'))
    self.assertEqual(
        self.empty.unique_id,
        (None, None))

  def testUpdateTime(self):
    self.assertEqual(
        self.ci.update_time,
        datetime(
            year=2014,
            month=3,
            day=11,
            hour=0,
            minute=20,
            second=8,
            microsecond=946000))

    self.assertIsNone(self.empty.update_time)

  def testCreatedTime(self):
    self.assertEqual(
        self.ci.created_time,
        datetime(
            year=2014,
            month=2,
            day=11,
            hour=12,
            minute=14,
            second=28,
            microsecond=135200))

    self.assertIsNone(self.empty.created_time)

  def testRevisions(self):
    self.assertEqual(
        self.ci.revisions,
        tuple(self._buildRevisionInfo(self.ci, revision_hash)
            for revision_hash in ('THIRD', 'SECOND', 'FIRST')))

    self.assertEqual(
        self.empty.revisions,
        ())

  def testRevisionInfoForNumber(self):
    self.assertEqual(
        self.ci.revisionInfoForNumber(3),
        self._buildRevisionInfo(self.ci, 'THIRD'))

    self.assertEqual(
        self.ci.revisionInfoForNumber(2),
        self._buildRevisionInfo(self.ci, 'SECOND'))

    self.assertEqual(
        self.ci.revisionInfoForNumber(1),
        self._buildRevisionInfo(self.ci, 'FIRST'))

  def testLatestRevision(self):
    # Implicit via 'revisions'
    self.assertEqual(
        self.ci.latest_revision,
        self._buildRevisionInfo(self.ci, 'THIRD'))

    # Explicit 'current_revision'
    ci = self.ci.extend(
        current_revision='FOURTH',
        revisions=self.ci['revisions'].extend(
            FOURTH={
                '_number': 4,
            },
        ),
    )
    self.assertEqual(
        ci.latest_revision,
        self._buildRevisionInfo(ci, 'FOURTH'))

    # Empty
    self.assertIsNone(self.empty.latest_revision)

  def testOwner(self):
    # Make sure Owner is an AccountInfo
    self.assertTrue(isinstance(self.ci.owner, AccountInfo))
    self.assertEqual(self.ci.owner['name'], 'Some Person')

  def testLabels(self):
    self.assertTrue(self.ci.label('Test-Label').isApproved())
    self.assertTrue(self.ci.label('Test-Label').isRejected())

    self.assertFalse(self.ci.label('Other-Label').isApproved())
    self.assertFalse(self.ci.label('Other-Label').isRejected())
    self.assertFalse(self.ci.label('Other-Label').isDisliked())

    self.assertIsNone(self.ci.label('Nonexistent-Label'))

  def testMessages(self):
    self.assertEqual(len(self.ci.messages), 0)

    self.assertEqual(len(self.msgci.messages), 2)
    self.assertEqual(self.msgci.messages[0]['id'], 1)
    self.assertEqual(self.msgci.messages[1]['id'], 2)


class ChangeMessageInfoTestCase(unittest.TestCase):

  def setUp(self):
    self.msg = ChangeMessageInfo.fromJsonDict({
        'id': 1,
        'author': 'test-user@test.org',
        'date': '2014-02-11 12:10:14.311200000',
        'message': 'MESSAGE1',
    })

  def testDate(self):
    self.assertEqual(
        self.msg.date,
        datetime(
            year=2014,
            month=2,
            day=11,
            hour=12,
            minute=10,
            second=14,
            microsecond=311200))


class LabelInfoTestCase(unittest.TestCase):

  def setUp(self):
    self.l = LabelInfo.fromJsonDict({
        'all': [
            {'value': 1},
            {'value': -2},
            {'value': -1},
        ],
        'approved': {},
        'rejected': {},
    })

    self.empty = LabelInfo.fromJsonDict({})

  def testQualities(self):
    self.assertTrue(self.l.isApproved())
    self.assertTrue(self.l.isRejected())
    self.assertFalse(self.l.isRecommended())
    self.assertFalse(self.l.isDisliked())

    self.assertFalse(self.empty.isApproved())
    self.assertFalse(self.empty.isRejected())
    self.assertFalse(self.empty.isRecommended())
    self.assertFalse(self.empty.isDisliked())

  def testValues(self):
    self.assertEqual(
        self.l.values,
        (-2, -1, 1))

    self.assertEqual(
        self.empty.values,
        ())


class AccountInfoTestCase(unittest.TestCase):

  def setUp(self):
    self.ai = AccountInfo.fromJsonDict({
        '_account_id': 12345,
        'name': 'Test User',
        'email': 'test-user@test.org',
        'username': 'test-user',
    })
    self.min_ai = AccountInfo.fromJsonDict({
        '_account_id': 12346,
    })

  def testBasic(self):
    self.assertEqual(self.ai['_account_id'], 12345)
    self.assertEqual(self.min_ai['_account_id'], 12346)


class ApprovalInfoTestCase(unittest.TestCase):

  def setUp(self):
    self.ai = ApprovalInfo.fromJsonDict({
        'value': 1,
        'date': '2013-02-01 09:59:32.126000000',
        '_account_id': 12345,
        'name': 'Test User',
        'email': 'test-user@test.org',
        'username': 'test-user',
    })
    self.min_ai = ApprovalInfo.fromJsonDict({
        '_account_id': 12346,
    })

  def testIsPermitted(self):
    self.assertTrue(self.ai.isPermitted)
    self.assertFalse(self.min_ai.isPermitted)

  def testDate(self):
    self.assertEqual(
        self.ai.date,
        datetime(
            year=2013,
            month=2,
            day=1,
            hour=9,
            minute=59,
            second=32,
            microsecond=126000,
        )
    )
    self.assertIsNone(self.min_ai.date)


class ReviewInputTestCase(unittest.TestCase):

  def setUp(self):
    self.ri = ReviewInput.New(
        message='Test',
        strict_labels=True,
        drafts=ReviewInput.DRAFTS_DELETE,
        notify=ReviewInput.NOTIFY_NONE,
        on_behalf_of=12345,
        )


  def testConstruct(self):
    self.assertEqual(
        ReviewInput.New().data,
        {})

    self.assertEqual(
        self.ri.data,
        {
            'message': 'Test',
            'strict_labels': True,
            'drafts': ReviewInput.DRAFTS_DELETE,
            'notify': ReviewInput.NOTIFY_NONE,
            'on_behalf_of': 12345,
        })

  def testAddLabel(self):
    ri = self.ri.addLabel('Code-Review', 1)
    ri = ri.addLabel('Other-Label', -1)

    self.assertEqual(
        ri.data,
        {
            'message': 'Test',
            'strict_labels': True,
            'drafts': ReviewInput.DRAFTS_DELETE,
            'notify': ReviewInput.NOTIFY_NONE,
            'on_behalf_of': 12345,
            'labels': {
                'Code-Review': 1,
                'Other-Label': -1,
            },
        })


if __name__ == '__main__':
  unittest.main()
