#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for common.gerrit's 'query.py'"""

import test_env  # pylint: disable=W0611
import unittest

from common.gerrit.query import QueryBuilder


class QueryBuilderTestCase(unittest.TestCase):

  def testEmptyQuery(self):
    q = QueryBuilder.New()
    self.assertEqual(str(q), "")
    self.assertEqual(len(q), 0)

  def testUnquoted(self):
    self.assertEqual(
        str(QueryBuilder.New().addUnquoted('Code-Review')),
        'Code-Review')

    self.assertEqual(
        str(QueryBuilder.New().addUnquoted('Code-Review=+1')),
        'Code-Review=+1')

    self.assertEqual(
        str(QueryBuilder.New().
            addUnquoted('Code-Review=+1').
            addUnquoted('Other=+2')),
        'Code-Review=+1+Other=+2')

  def testQuoted(self):
    self.assertEqual(
        str(QueryBuilder.New().addQuoted('Code-Review')),
        'Code-Review')

    self.assertEqual(
        str(QueryBuilder.New().addQuoted('Code-Review=+1')),
        'Code-Review%3D%2B1')

    self.assertEqual(
        str(QueryBuilder.New().
            addQuoted('Code-Review=+1').
            addQuoted('Other=+2')),
        'Code-Review%3D%2B1+Other%3D%2B2')

  def testTerms(self):
    self.assertEqual(
        str(QueryBuilder.New().addSelector('a', 'b')),
        'a:b')

    self.assertEqual(
        str(QueryBuilder.New().addSelector('a+a', 'b+b')),
        'a%2Ba:b%2Bb')

    self.assertEqual(
        str(QueryBuilder.New().
            addSelector('a+a', 'b+b').
            addSelector('label', 'Code-Review=+2')),
        'a%2Ba:b%2Bb+label:Code-Review%3D%2B2')

  def testMixed(self):
    self.assertEqual(
        str(QueryBuilder.New(
            'label:Code-Review=+0',
            'status:open',
            'random-term',
            )),
        'label:Code-Review%3D%2B0+status:open+random-term')

  def testOperator(self):
    self.assertEqual(
        str(QueryBuilder.NewOR()),
        '')

    self.assertEqual(
        str(QueryBuilder.NewOR().
            addUnquoted('test1')),
        'test1')

    self.assertEqual(
        str(QueryBuilder.NewOR().
            addUnquoted('test1').
            addUnquoted('test2').
            addUnquoted('test3')),
        'test1+OR+test2+OR+test3')

  def testNestedQueryBuilders(self):
    self.assertEqual(
        str(QueryBuilder.New(
            'status:open',
            QueryBuilder.NewOR(
                'label:Code-Review=+0',
                'status:open',
            ),
            'test1',
            'test2')),
        'status:open+(label:Code-Review%3D%2B0+OR+status:open)+test1+test2')

    self.assertEqual(
        str(QueryBuilder.New(
            'status:open',
            QueryBuilder.NewOR(
                'label:Code-Review=+0',
                'status:open',
                QueryBuilder.NewAND(
                    'status:new',
                    'label:Code-Review=-0',
                ),
            ),
            'test1',
            'test2')),
        'status:open+(label:Code-Review%3D%2B0+OR+status:open+OR+'
        '(status:new+AND+label:Code-Review%3D-0))+test1+test2')

    # Empty nested QueryBuilder should add no terms
    self.assertEqual(
        str(QueryBuilder.New(
            'status:open',
            QueryBuilder.New(),
            'test1',
            'test2')),
        'status:open+test1+test2')
    #
    # Empty nested QueryBuilder should add no terms
    self.assertEqual(
        str(QueryBuilder.New(
            QueryBuilder.New(),
            QueryBuilder.New(),
            QueryBuilder.New(),
            QueryBuilder.New(),
            )),
        '')

  def testNestedLists(self):
    self.assertEqual(
        str(QueryBuilder.New(
            'status:open',
            [
                'label:Code-Review=+0',
                'status:open',
                [
                    'status:new',
                    'label:Code-Review=-0',
                ],
            ],
            'test1',
            'test2')),
        'status:open+(label:Code-Review%3D%2B0+status:open+'
        '(status:new+label:Code-Review%3D-0))+test1+test2')

if __name__ == '__main__':
  unittest.main()
