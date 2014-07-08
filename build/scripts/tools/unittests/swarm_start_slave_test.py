#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import test_env  # pylint: disable=W0611
from common import find_depot_tools  # pylint: disable=W0611

import mock

from testing_support import auto_stub

SWARM_BOOTSTRAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'swarm_bootstrap')
sys.path.insert(0, SWARM_BOOTSTRAP_DIR)

import start_slave


class Options(object):
  def __init__(self):
    self.swarm_server = 'http://dummy-swarm-server.com'
    self.port = '443'


class MockOptParser(object):
  def __init__(self, description):
    pass

  def add_option(self, _short_flag, _long_flag):
    pass

  def parse_args(self):  # pylint:disable=R0201
    return Options(), []


class SwarmStartSlaveTest(auto_stub.TestCase):
  def setUp(self):
    super(SwarmStartSlaveTest, self).setUp()

    # Ensure that none of the tests try to actually write files.
    self.mock(start_slave, 'WriteToFile', mock.Mock())

  def test_dimensions(self):
    # These two require some logic that doesn't need to be tested here. Just
    # test GetchromiumDimensions() work fine.
    bits = start_slave.GetArchitectureSize()
    machine = start_slave.GetMachineType()
    actual = start_slave.GetChromiumDimensions('s33-c4', 'darwin', '10.8')
    expected = {
        'dimensions': {
          'bits': bits,
          'hostname': 's33-c4',
          'machine': machine,
          'os': ['Mac', 'Mac-10.8'],
          'vlan': 'm4',
        },
        'tag': 's33-c4',
    }
    self.assertEqual(expected, actual)

    actual = start_slave.GetChromiumDimensions('vm1-m4', 'linux2', '12.04')
    expected = {
        'dimensions': {
          'bits': bits,
          'hostname': 'vm1-m4',
          'machine': machine,
          'os': ['Linux', 'Linux-12.04'],
          'vlan': 'm4',
        },
        'tag': 'vm1-m4',
    }
    self.assertEqual(expected, actual)

    actual = start_slave.GetChromiumDimensions('vm1-m1', 'win32', '7')
    expected = {
        'dimensions': {
          'bits': bits,
          'hostname': 'vm1-m1',
          'machine': machine,
          'os': ['Windows', 'Windows-7'],
          'vlan': 'm1',
        },
        'tag': 'vm1-m1',
    }
    self.assertEqual(expected, actual)

  def test_mac_mapping(self):
    self.assertEqual('10.7', start_slave.ConvertMacVersion('10.7.2'))
    self.assertEqual('10.8', start_slave.ConvertMacVersion('10.8.4'))
    self.assertEqual('10.9', start_slave.ConvertMacVersion('10.9'))

  def test_windows_mapping(self):
    self.assertEqual('5.1', start_slave.ConvertWindowsVersion('5.1.2505'))
    self.assertEqual('5.1',
                     start_slave.ConvertWindowsVersion('5.1.2600.2180'))
    self.assertEqual(
        '5.1',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-5.1.2600'))

    self.assertEqual('6.0', start_slave.ConvertWindowsVersion('6.0.5048'))
    self.assertEqual(
        '6.0',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-6.0.5048'))

    self.assertEqual('6.1',
                     start_slave.ConvertWindowsVersion('6.1.7600.16385'))
    self.assertEqual(
        '6.1',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-6.1.7601'))

    self.assertEqual('6.2', start_slave.ConvertWindowsVersion('6.2.9200'))
    self.assertEqual(
        '6.2',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-6.2.9200'))

  def test_convert_cygwin_path(self):
    self.assertEqual(None, start_slave.ConvertCygwinPath('/b/path'))
    self.assertEqual(None, start_slave.ConvertCygwinPath('c:\\temp.txt'))

    self.assertEqual('e:\\b\\swarm_slave',
                     start_slave.ConvertCygwinPath('/cygdrive/e/b/swarm_slave'))

    self.assertEqual(
        'c:\\b\\swarm_slave\\slave_machine.py',
        start_slave.ConvertCygwinPath(
            '/cygdrive/c/b/swarm_slave/slave_machine.py'))

  def check_start_slave_main(self, platform):
    """Calls start_slave main and ensure it doesn't crash for the given
    platform.
    """
    self.mock(start_slave.optparse, 'OptionParser', MockOptParser)
    self.mock(start_slave.sys, 'platform', platform)

    start_slave.main()

  def test_main_linux(self):  # pylint: disable=R0201
    self.check_start_slave_main('linux2')

  def test_main_mac(self):  # pylint: disable=R0201
    self.mock(start_slave.platform, 'mac_ver',
              mock.Mock(return_value=('10.7', (), '')))

    self.check_start_slave_main('darwin')

  def test_main_win(self):  # pylint: disable=R0201
    self.mock(start_slave.platform, 'version', mock.Mock(return_value='5.1'))

    self.check_start_slave_main('win32')


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
