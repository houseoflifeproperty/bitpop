#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts all masters and verify they can server /json/project fine.
"""

import logging
import optparse
import os
import subprocess
import sys
import time

import masters_util


def do_master_imports():
  # Import scripts/slave/bootstrap.py to get access to the ImportMasterConfigs
  # function that will pull in every site_config for us. The master config
  # classes are saved as attributes of config_bootstrap.Master. The import
  # takes care of knowing which set of site_configs to use.
  import slave.bootstrap
  slave.bootstrap.ImportMasterConfigs()
  return getattr(sys.modules['config_bootstrap'], 'Master')


def test_master(master, master_class, path):
  print('Trying %s' % master)
  start = time.time()
  if not masters_util.stop_master(master, path):
    return False
  # Try to backup twistd.log
  twistd_log = os.path.join(path, 'twistd.log')
  had_twistd_log = os.path.isfile(twistd_log)
  # Try to backup a Git workdir.
  git_workdir = os.path.join(path, 'git_poller_src.git')
  had_git_workdir = os.path.isdir(git_workdir)
  try:
    if had_twistd_log:
      os.rename(twistd_log, twistd_log + '_')
    if had_git_workdir:
      if subprocess.call(['mv', git_workdir, git_workdir + '_']) != 0:
        print >> sys.stderr, 'ERROR: Failed to rename %s' % git_workdir
    try:
      if not masters_util.start_master(master, path):
        return False
      name = master_class.project_name
      port1 = master_class.master_port
      port2 = master_class.master_port_alt
      # We pass both the read/write and read-only ports, even though querying
      # either one alone would be sufficient sign of success.
      res = masters_util.wait_for_start(master, name, path, [port1, port2])
      if res:
        logging.info('Success in %1.1fs' % (time.time() - start))
      return res
    finally:
      masters_util.stop_master(master, path)
  finally:
    if had_twistd_log:
      os.rename(twistd_log + '_', twistd_log)
    if (os.path.isdir(git_workdir) and
        subprocess.call(['rm', '-rf', git_workdir]) != 0):
      print >> sys.stderr, 'ERROR: Failed to remove %s' % git_workdir
    if had_git_workdir:
      if subprocess.call(['mv', git_workdir + '_', git_workdir]) != 0:
        print >> sys.stderr, 'ERROR: Failed to rename %s' % (git_workdir + '_')


def real_main(base_dir, expected):
  expected = expected.copy()
  parser = optparse.OptionParser()
  parser.add_option('-v', '--verbose', action='count', default=0)
  options, args = parser.parse_args()
  if args:
    parser.error('Unsupported args %s' % ' '.join(args))
  levels = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)
  logging.basicConfig(level=levels[min(options.verbose, len(levels)-1)])

  start = time.time()
  base = os.path.join(base_dir, 'masters')
  master_classes = do_master_imports()
  # Here we look for a slaves.cfg file in the directory to ensure that
  # the directory actually contains a master, as opposed to having existed
  # at one time but later having been removed.  In the latter case, it's
  # no longer an actual master that should be 'discovered' by this test.
  masters = sorted(
      p for p in os.listdir(base)
      if (os.path.isfile(os.path.join(base, p, 'slaves.cfg')) and
          not p.startswith('.'))
  )

  failed = set()
  skipped = 0
  success = 0

  # First make sure no master is started. Otherwise it could interfere with
  # conflicting port binding.
  if not masters_util.check_for_no_masters():
    return 1
  for master in masters:
    pid_path = os.path.join(base, master, 'twistd.pid')
    if os.path.isfile(pid_path):
      pid_value = int(open(pid_path).read().strip())
      if masters_util.pid_exists(pid_value):
        print >> sys.stderr, ('%s is still running as pid %d.' %
            (master, pid_value))
        print >> sys.stderr, 'Please stop it before running the test.'
        return 1

  bot_pwd_path = os.path.join(
      base_dir, '..', 'build', 'site_config', '.bot_password')
  need_bot_pwd = not os.path.isfile(bot_pwd_path)
  try:
    if need_bot_pwd:
      with open(bot_pwd_path, 'w') as f:
        f.write('foo\n')
    for master in masters[:]:
      if not master in expected:
        continue

      apply_issue_pwd_path = os.path.join(base, master, '.apply_issue_password')
      need_apply_issue_pwd = not os.path.isfile(apply_issue_pwd_path)
      try:
        if need_apply_issue_pwd:
          with open(apply_issue_pwd_path, 'w') as f:
            f.write('foo\n')
        masters.remove(master)
        classname = expected.pop(master)
        if not classname:
          skipped += 1
          continue
        master_class = getattr(master_classes, classname)
        if not test_master(master, master_class, os.path.join(base, master)):
          failed.add(master)
        else:
          success += 1
      finally:
        if need_apply_issue_pwd:
          os.remove(apply_issue_pwd_path)
  finally:
    if need_bot_pwd:
      os.remove(bot_pwd_path)

  if failed:
    print >> sys.stderr, (
        '%d masters failed:\n%s' % (len(failed), '\n'.join(sorted(failed))))
  if masters:
    print >> sys.stderr, (
        '%d masters were not expected:\n%s' %
        (len(masters), '\n'.join(sorted(masters))))
  if expected:
    print >> sys.stderr, (
        '%d masters were expected but not found:\n%s' %
        (len(expected), '\n'.join(sorted(expected))))
  print >> sys.stderr, (
      '%s masters succeeded, %d failed, %d skipped in %1.1fs.' % (
        success, len(failed), skipped, time.time() - start))
  return int(bool(masters or expected or failed))


def main():
  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  sys.path.extend(os.path.normpath(os.path.join(base_dir, d)) for d in (
      'site_config',
      os.path.join('..', 'build_internal', 'site_config'),
  ))
  expected = {
      'master.chromium': 'Chromium',
      'master.chromium.chrome': 'ChromiumChrome',
      'master.chromium.chromebot': 'ChromiumChromebot',
      'master.chromium.chromiumos': 'ChromiumChromiumOS',
      'master.chromium.endure': 'ChromiumEndure',
      'master.chromium.flaky': 'ChromiumFlaky',
      'master.chromium.fyi': 'ChromiumFYI',
      'master.chromium.git': 'ChromiumGIT',
      'master.chromium.gpu': 'ChromiumGPU',
      'master.chromium.gpu.fyi': 'ChromiumGPUFYI',
      'master.chromium.linux': 'ChromiumLinux',
      'master.chromium.lkgr': 'ChromiumLKGR',
      'master.chromium.mac': 'ChromiumMac',
      'master.chromium.memory': 'ChromiumMemory',
      'master.chromium.memory.fyi': 'ChromiumMemoryFYI',
      'master.chromium.perf': 'ChromiumPerf',
      'master.chromium.perf_av': 'ChromiumPerfAv',
      'master.chromium.pyauto': 'ChromiumPyauto',
      'master.chromium.swarm': 'ChromiumSwarm',
      'master.chromium.unused': None,
      'master.chromium.webkit': 'ChromiumWebkit',
      'master.chromium.webrtc': 'ChromiumWebRTC',
      'master.chromium.win': 'ChromiumWin',
      'master.chromiumos': 'ChromiumOS',
      'master.chromiumos.tryserver': None,
      'master.chromiumos.unused': None,
      'master.client.drmemory': 'DrMemory',
      'master.client.dynamorio': 'DynamoRIO',
      'master.client.dart': 'Dart',
      'master.client.dart.fyi': 'DartFYI',
      'master.client.nacl': 'NativeClient',
      'master.client.nacl.chrome': 'NativeClientChrome',
      'master.client.nacl.llvm': 'NativeClientLLVM',
      'master.client.nacl.ports': 'NativeClientPorts',
      'master.client.nacl.ragel': 'NativeClientRagel',
      'master.client.nacl.sdk': 'NativeClientSDK',
      'master.client.nacl.sdk.addin': 'NativeClientSDKAddIn',
      'master.client.nacl.sdk.mono': 'NativeClientSDKMono',
      'master.client.nacl.toolchain': 'NativeClientToolchain',
      'master.client.omaha': 'Omaha',
      'master.client.pagespeed': 'PageSpeed',
      'master.client.sfntly': None,
      'master.client.skia': None,
      'master.client.syzygy': None,
      'master.client.tsan': None,  # make start fails
      'master.client.unused': None,
      'master.client.v8': 'V8',
      'master.client.webrtc': 'WebRTC',
      'master.experimental': None,
      'master.reserved': None,  # make start fails
      'master.tryserver.chromium': 'TryServer',
      'master.tryserver.nacl': 'NativeClientTryServer',
      'master.tryserver.unused': None,
      'master.devtools': 'DevTools',
      'master.webkit': None,
  }
  return real_main(base_dir, expected)


if __name__ == '__main__':
  sys.exit(main())
