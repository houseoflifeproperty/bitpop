#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0403,W0611

import unittest

import slave.slave_utils as slave_utils


class TestGypFlags(unittest.TestCase):

  # So that python 2.6 can test this.
  def AssertIsNone(self, x, msg=None):
    self.assertTrue(x is None, msg=msg)

  def test_single_gyp_flag_one(self):
    self.assertEqual(
        slave_utils.GetGypFlag({'factory_properties': {
            'gclient_env': { 'GYP_DEFINES' : 'chromeos=1' },
            'trigger': 'chromiumos_dbg_trigger',
            'window_manager': False,
            }}, 'chromeos'), '1')

  def test_single_gyp_flag_zero(self):
    self.assertEqual(
        slave_utils.GetGypFlag({'factory_properties': {
            'gclient_env': { 'GYP_DEFINES' : 'chromeos=0' },
            'trigger': 'chromiumos_dbg_trigger',
            'window_manager': False,
            }}, 'chromeos'), '0')

  def test_triple_gyp_flag_center(self):
    self.assertEqual(
        slave_utils.GetGypFlag({'factory_properties': {
            'gclient_env': { 'GYP_DEFINES' : 'bull tiger=x03 frog' },
            }}, 'tiger'), 'x03')

  def test_gyp_flag_not_present(self):
    self.AssertIsNone(
        slave_utils.GetGypFlag({'factory_properties': {
            'gclient_env': { 'GYP_DEFINES' : 'tiger=1' },
            }}, 'chromeos'))

  def test_triple_gyp_flag_last(self):
    self.assertTrue(
        slave_utils.GetGypFlag({'factory_properties': {
            'gclient_env': { 'GYP_DEFINES' : 'tiger=1 buffalo giraffe' }}},
            'giraffe'))

  def test_no_gyp_flags_with_other(self):
    self.AssertIsNone(
        slave_utils.GetGypFlag({'factory_properties': {
            'gclient_env': { 'OTHER_DEFINES' : 'tiger=1' }}},
            'tiger'))

  def test_no_gyp_flags(self):
    self.AssertIsNone(
        slave_utils.GetGypFlag({'factory_properties': {}}, 'chromeos'))

  def test_no_properties_flags(self):
    self.AssertIsNone(slave_utils.GetGypFlag({}, 'chromeos'))



class TestGypFlagIsOn(unittest.TestCase):

  def testSample(self):
    sample = {'factory_properties': {'gclient_env': { 'GYP_DEFINES' :
        'tiger=1 buffalo=0 giraffe' }}}
    self.assertTrue(slave_utils.GypFlagIsOn(sample, 'tiger'))
    self.assertFalse(slave_utils.GypFlagIsOn(sample, 'buffalo'))
    self.assertTrue(slave_utils.GypFlagIsOn(sample, 'giraffe'))
    self.assertFalse(slave_utils.GypFlagIsOn(sample, 'monkey'))


if __name__ == '__main__':
  unittest.main()
