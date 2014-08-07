#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Annotated script to launch the gatekeeper script."""

import os
import sys

SLAVE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SLAVE_DIR, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts', 'slave'))

from common import annotator
from common import chromium_utils


def gen_gatekeeper_cmd(master_urls, extra_args=None):
  json = os.path.join(SLAVE_DIR, 'gatekeeper.json')
  args = ['-v', '--json=%s' % json]

  script = os.path.join(SLAVE_DIR, 'gatekeeper_ng.py')
  cmd = [sys.executable, script]

  cmd.extend(args)

  if extra_args:
    cmd.extend(extra_args)

  cmd.extend(master_urls)
  return cmd


def run_gatekeeper(master_urls, extra_args=None):
  env = {}
  env['PYTHONPATH'] = os.pathsep.join(sys.path)

  cmd = gen_gatekeeper_cmd(master_urls, extra_args=extra_args)

  return chromium_utils.RunCommand(cmd, env=env)


def main():
  stream = annotator.StructuredAnnotationStream(seed_steps=[
      'gatekeeper_ng',
      'waterfall_gatekeeper',
      'blink_gatekeeper'])

  with stream.step('gatekeeper non-closure') as s:
    master_urls = ['http://build.chromium.org/p/chromium',
                   'http://build.chromium.org/p/chromium.lkgr',
                   'http://build.chromium.org/p/chromium.perf',
                   'http://build.chromium.org/p/client.libvpx',
    ]

    if run_gatekeeper(master_urls) != 0:
      s.step_failure()
      return 2

  with stream.step('waterfall_gatekeeper') as s:
    status_url = 'https://chromium-status.appspot.com'

    master_urls = ['http://build.chromium.org/p/chromium.gpu']

    extra_args = ['--build-db=waterfall_build_db.json', '-s',
                  '--status-url=%s' % status_url,
                  '--track-revisions',
                  '--password-file=.status_password']

    if run_gatekeeper(master_urls, extra_args=extra_args) != 0:
      s.step_failure()
      return 2

  with stream.step('blink_gatekeeper') as s:
    status_url = 'https://blink-status.appspot.com'

    master_urls = ['http://build.chromium.org/p/chromium.webkit']

    extra_args = ['--build-db=blink_build_db.json', '-s',
                  '--status-url=%s' % status_url,
                  '--track-revisions',
                  '--revision-properties', 'got_revision,got_webkit_revision',
                  '--password-file=.blink_status_password']

    if run_gatekeeper(master_urls, extra_args=extra_args) != 0:
      s.step_failure()
      return 2
  return 0


if '__main__' == __name__:
  sys.exit(main())
