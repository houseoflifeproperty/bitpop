# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Scheduler
# This is due to buildbot 0.7.12 being used for the presubmit check.
from buildbot.changes.filter import ChangeFilter  # pylint: disable=E0611,F0401

from master.factory import syzygy_factory


def win():
  return syzygy_factory.SyzygyFactory('src/build',
                                      target_platform='win32')


def _VersionFileFilter(change):
  """A change filter function that disregards all changes that don't
  touch src/syzygy/VERSION.

  Args:
      change: a buildbot Change object.
  """
  return change.branch == 'trunk' and 'syzygy/VERSION' in change.files

#
# Official build scheduler for Syzygy
#
official_scheduler = Scheduler('syzygy_version',
                               treeStableTimer=0,
                               change_filter=ChangeFilter(
                                  filter_fn=_VersionFileFilter),
                               builderNames=['Syzygy Official'])

#
# Windows official Release builder
#
official_factory = win().SyzygyFactory(official_release=True)

official_builder = {
    'name': 'Syzygy Official',
    'factory': official_factory,
    'schedulers': 'syzygy_version',
    'auto_reboot': False,
    'category': 'official',
    }


def Update(config, active_master, c):
  c['schedulers'].append(official_scheduler)
  c['builders'].append(official_builder)
