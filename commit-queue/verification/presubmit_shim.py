#!/usr/bin/env python
# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Runs presubmit check on the source tree.

This shims removes the checks for try jobs.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ROOT_DIR))

import find_depot_tools  # pylint: disable=W0611
import presubmit_support


# Replace the try job and tree status presubmit checsk since the commit queue
# will do its own try job runs and its own tree status check before committing.
def NoopCannedCheck(*_args, **_kwargs):
  return []

presubmit_support.presubmit_canned_checks.CheckRietveldTryJobExecution = (
    NoopCannedCheck)
presubmit_support.presubmit_canned_checks.CheckTreeIsOpen = (
    NoopCannedCheck)
presubmit_support.presubmit_canned_checks.CheckBuildbotPendingBuilds = (
    NoopCannedCheck)

# Do not pass them through the command line.
email = sys.stdin.readline().strip()
assert email
password = sys.stdin.readline().strip()
assert password

argv = sys.argv[1:]
argv.extend(['--rietveld_email', email, '--rietveld_password', password])
sys.stdin.close()

sys.exit(presubmit_support.Main(argv))
