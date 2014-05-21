# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Scheduler
# This is due to buildbot 0.7.12 being used for the presubmit check.
from buildbot.changes.filter import ChangeFilter  # pylint: disable=E0611,F0401

from master.factory import syzygy_factory


def win():
  return syzygy_factory.SyzygyFactory('src/build',
                                      target_platform='win32')


def _BinariesFilter(change):
  """A change filter function that disregards all changes that don't
  touch src/syzygy/binaries/*.

  Args:
      change: a buildbot Change object.
  """
  if change.branch != 'trunk':
    return False
  for path in change.files:
    if path.startswith('syzygy/binaries/'):
      return True
  return False


# Binaries scheduler for Syzygy.
binaries_scheduler = Scheduler('syzygy_binaries',
                               treeStableTimer=0,
                               change_filter=ChangeFilter(
                                   filter_fn=_BinariesFilter),
                               builderNames=['Syzygy Smoke Test'])


# Windows binaries smoke-test builder for Syzygy.
smoke_test_factory = win().SyzygySmokeTestFactory()


smoke_test_builder = {
  'name': 'Syzygy Smoke Test',
  'factory': smoke_test_factory,
  'schedulers': 'syzygy_binaries',
  'auto_reboot': False,
  'category': 'official',
}


def Update(config, active_master, c):
  c['schedulers'].append(binaries_scheduler)
  c['builders'].append(smoke_test_builder)
