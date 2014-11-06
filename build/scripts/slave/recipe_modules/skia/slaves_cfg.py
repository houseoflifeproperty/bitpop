# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Utilities for working with slaves.cfg files."""


import os


def _slaves_cfg_path(master_name):
  return os.path.abspath(os.path.join(
      os.path.abspath(os.path.dirname(__file__)),
      os.pardir, os.pardir, os.pardir, os.pardir, 'masters',
      'master.' + master_name, 'slaves.cfg'))


def get(master_name):
  """Return a dictionary of the buildslaves for the given master.

  Keys are slavenames and values are the unmodified slave dicts from the
  slaves.cfg file for the given master.
  """
  vars = {}
  execfile(_slaves_cfg_path(master_name), vars)
  slaves_cfg = {}
  for slave_dict in vars['slaves']:
    slaves_cfg[slave_dict['hostname']] = slave_dict
  return slaves_cfg

