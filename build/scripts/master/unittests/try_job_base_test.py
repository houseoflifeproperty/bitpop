#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""try_job_base.py testcases."""

import unittest

import test_env  # pylint: disable=W0611

from master import try_job_base


class PaseOptionsTest(unittest.TestCase):
  def setUp(self):
    self.DEFAULT = 'DEFAULT'
    self.VALID_KEYS = ['linux', 'linux_chromeos',  'mac', 'win']

  @staticmethod
  def _get_default():
    return {
        'bot': {},
        'branch': None,
        'clobber': False,
        'email': [],
        'issue': None,
        'name': 'Unnamed',
        'orig_revision': None,
        'patch': None,
        'patchlevel': 0,
        'patchset': None,
        'project': None,
        'reason': 'John Doe: Unnamed',
        'requester': None,
        'repository': None,
        'revision': None,
        'root': None,
        'testfilter': [],
        'user': 'John Doe',
    }

  def test_parse_options_defaults(self):
    values = {'bot': ['win', 'win:foo']}
    expected = self._get_default()
    expected['bot'] = {
      # It is important to note:
      # - The set is converted into a list.
      # - try_job_base.DEFAULT_TESTS was added because the builder was speficied
      #   on a single line.
      'win': [try_job_base.DEFAULT_TESTS, 'foo'],
    }
    self.assertEquals(
        expected,
        try_job_base.parse_options(values, self.VALID_KEYS, None))

  def test_parse_options_clobber_true(self):
    values = {'bot': ['win'], 'clobber': ['true']}
    expected = self._get_default()
    expected['bot'] = {'win': [try_job_base.DEFAULT_TESTS]}
    expected['clobber'] = True
    self.assertEquals(
        expected,
        try_job_base.parse_options(values, self.VALID_KEYS, None))

  def test_parse_options_clobber_false(self):
    values = {'bot': ['win'], 'clobber': ['false']}
    expected = self._get_default()
    expected['bot'] = {'win': [try_job_base.DEFAULT_TESTS]}
    self.assertEquals(
        expected,
        try_job_base.parse_options(values, self.VALID_KEYS, None))

  def test_dict_comma_not_key(self):
    result = try_job_base.dict_comma(['foo'], self.VALID_KEYS, self.DEFAULT)
    expected = {}
    self.assertEquals(expected, result)

  def test_dict_comma_trailing_comma(self):
    try:
      try_job_base.dict_comma(['win,'], self.VALID_KEYS, self.DEFAULT)
      self.fail()
    except try_job_base.BadJobfile:
      pass

  def test_dict_comma_state_1(self):
    values = ['win']
    expected = {'win': set([self.DEFAULT])}
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_1(self):
    values = ['win,linux']
    expected = {
        'linux': set([self.DEFAULT]),
        'win': set([self.DEFAULT]),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_1_drop(self):
    values = ['win,bar']
    expected = {'win': set([self.DEFAULT])}
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_2(self):
    values = ['win:foo']
    expected = {'win': set(['foo'])}
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_2_3(self):
    values = ['win:foo:bar']
    expected = {'win': set(['foo:bar'])}
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_2_3_bad(self):
    try:
      try_job_base.dict_comma(
          ['win:foo:bar:baz'], self.VALID_KEYS, self.DEFAULT)
      self.fail()
    except try_job_base.BadJobfile:
      pass

  def test_dict_comma_state_1_2_3_4_value1(self):
    values = ['win:foo:bar,linux']
    expected = {
      'win': set(['foo:bar', 'linux']),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_2_3_4_value2(self):
    values = ['win:foo:bar,baz']
    expected = {
      'win': set(['foo:bar', 'baz']),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_2_3_4_3(self):
    values = ['win:test1:-filter1.*,test2:*.filter2']
    expected = {
      'win': set(['test1:-filter1.*', 'test2:*.filter2']),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_state_1_2_4_3(self):
    values = ['win:test1,test2:*.filter2']
    expected = {
      'win': set(['test1', 'test2:*.filter2']),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_merge(self):
    values = [
      # The currently supported formats are a bit messy while we transition
      # to something sane.
      'linux_chromeos,linux:test1',
      'linux:test2:foo.*',
      'mac,win',
      'mac,win',
    ]
    expected = {
      'linux': set(['test1', 'test2:foo.*']),
      'linux_chromeos': set([self.DEFAULT]),
      'mac': set([self.DEFAULT]),
      'win': set([self.DEFAULT]),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def test_dict_comma_life_like(self):
    values = [
      # Many builders on one line, with one including a test.:
      'linux,win,linux_chromeos:aura_unittests:Foo.*Bar,another_test:-*.*',
      # Specify multiple tests on one line:
      'mac:base_unittests,unit_tests',
      # Append a test to self.DEFAULT:
      'linux:slow_test_disabled_by_default',
    ]
    expected = {
      'linux': set([self.DEFAULT, 'slow_test_disabled_by_default']),
      'linux_chromeos': set(['aura_unittests:Foo.*Bar', 'another_test:-*.*']),
      'mac': set(['base_unittests', 'unit_tests']),
      'win': set([self.DEFAULT]),
    }
    self.assertEquals(
        expected,
        try_job_base.dict_comma(values, self.VALID_KEYS, self.DEFAULT))

  def testParseText(self):
    text = (
        'foo=bar\n'
        '\n'
        'Ignored text\n'
        'ignored_key=\n'
        '=ignored_value\n'
        'DUPE=dupe1\n'
        'DUPE=dupe2\n')
    expected = {
        'foo': ['bar'],
        'DUPE': ['dupe1', 'dupe2'],
    }
    self.assertEquals(expected, try_job_base.text_to_dict(text))


if __name__ == '__main__':
  unittest.main()
