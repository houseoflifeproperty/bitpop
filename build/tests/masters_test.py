#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts all masters and verify they can server /json/project fine.
"""

import collections
import contextlib
import glob
import logging
import optparse
import os
import subprocess
import sys
import tempfile
import threading
import time

BUILD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BUILD_DIR, 'scripts'))

from tools import runit
runit.add_build_paths(sys.path)

import masters_util
from common import chromium_utils
from common import master_cfg_utils


def do_master_imports():
  # Import scripts/slave/bootstrap.py to get access to the ImportMasterConfigs
  # function that will pull in every site_config for us. The master config
  # classes are saved as attributes of config_bootstrap.Master. The import
  # takes care of knowing which set of site_configs to use.
  import slave.bootstrap
  slave.bootstrap.ImportMasterConfigs()
  return getattr(sys.modules['config_bootstrap'], 'Master')


@contextlib.contextmanager
def BackupPaths(base_path, path_globs):
  tmpdir = tempfile.mkdtemp(prefix='.tmpMastersTest', dir=base_path)
  paths_to_restore = []
  try:
    for path_glob in path_globs:
      for path in glob.glob(os.path.join(base_path, path_glob)):
        bkup_path  = os.path.join(tmpdir, os.path.relpath(path, base_path))
        os.rename(path, bkup_path)
        paths_to_restore.append((path, bkup_path))
    yield
  finally:
    for path, bkup_path in paths_to_restore:
      if subprocess.call(['rm', '-rf', path]) != 0:
        print >> sys.stderr, 'ERROR: failed to remove tmp %s' % path
        continue
      if subprocess.call(['mv', bkup_path, path]) != 0:
        print >> sys.stderr, 'ERROR: mv %s %s' % (bkup_path, path)
    os.rmdir(tmpdir)

def test_master(master, path, name, ports):
  if not masters_util.stop_master(master, path):
    return False
  logging.info('%s Starting', master)
  start = time.time()
  with BackupPaths(path, ['twistd.log', 'twistd.log.?', 'git_poller_*.git',
                          'state.sqlite']):
    try:
      if not masters_util.start_master(master, path, dry_run=True):
        return False
      res = masters_util.wait_for_start(master, name, path, ports)
      if not res:
        logging.info('%s Success in %1.1fs', master, (time.time() - start))
      return res
    finally:
      masters_util.stop_master(master, path, force=True)


class MasterTestThread(threading.Thread):
  # Class static. Only access this from the main thread.
  port_lock_map = collections.defaultdict(threading.Lock)

  def __init__(self, master, master_class, master_path):
    super(MasterTestThread, self).__init__()
    self.master = master
    self.master_path = master_path
    self.name = master_class.project_name
    all_ports = [
        master_class.master_port, master_class.master_port_alt,
        master_class.slave_port, getattr(master_class, 'try_job_port', 0)]
    # Sort port locks numerically to prevent deadlocks.
    self.port_locks = [self.port_lock_map[p] for p in sorted(all_ports) if p]

    # We pass both the read/write and read-only ports, even though querying
    # either one alone would be sufficient sign of success.
    self.ports = [p for p in all_ports[:2] if p]
    self.result = None

  def run(self):
    with contextlib.nested(*self.port_locks):
      self.result = test_master(
          self.master, self.master_path, self.name, self.ports)


def real_main(all_expected):
  start = time.time()
  master_classes = do_master_imports()
  all_masters = {}
  for base in all_expected:
    base_dir = os.path.join(base, 'masters')
    all_masters[base] = sorted(p for p in
        os.listdir(base_dir) if
        os.path.exists(os.path.join(base_dir, p, 'master.cfg')))
  failed = set()
  skipped = 0
  success = 0

  # First make sure no master is started. Otherwise it could interfere with
  # conflicting port binding.
  if not masters_util.check_for_no_masters():
    return 1
  for base, masters in all_masters.iteritems():
    for master in masters:
      pid_path = os.path.join(base, 'masters', master, 'twistd.pid')
      if os.path.isfile(pid_path):
        pid_value = int(open(pid_path).read().strip())
        if masters_util.pid_exists(pid_value):
          print >> sys.stderr, ('%s is still running as pid %d.' %
              (master, pid_value))
          print >> sys.stderr, 'Please stop it before running the test.'
          return 1


  with master_cfg_utils.TemporaryMasterPasswords():
    master_threads = []
    for base, masters in all_masters.iteritems():
      for master in masters[:]:
        if not master in all_expected[base]:
          continue
        masters.remove(master)
        classname = all_expected[base].pop(master)
        if not classname:
          skipped += 1
          continue
        cur_thread = MasterTestThread(
            master=master,
            master_class=getattr(master_classes, classname),
            master_path=os.path.join(base, 'masters', master))
        cur_thread.start()
        master_threads.append(cur_thread)
      for cur_thread in master_threads:
        cur_thread.join(20)
        if cur_thread.result:
          print '\n=== Error running %s === ' % cur_thread.master
          print cur_thread.result
          failed.add(cur_thread.master)
        else:
          success += 1

  if failed:
    print >> sys.stderr, (
        '%d masters failed:\n%s' % (len(failed), '\n'.join(sorted(failed))))
  remaining_masters = []
  for masters in all_masters.itervalues():
    remaining_masters.extend(masters)
  if any(remaining_masters):
    print >> sys.stderr, (
        '%d masters were not expected:\n%s' %
        (len(remaining_masters), '\n'.join(sorted(remaining_masters))))
  outstanding_expected = []
  for expected in all_expected.itervalues():
    outstanding_expected.extend(expected)
  if outstanding_expected:
    print >> sys.stderr, (
        '%d masters were expected but not found:\n%s' %
        (len(outstanding_expected), '\n'.join(sorted(outstanding_expected))))
  print >> sys.stderr, (
      '%s masters succeeded, %d failed, %d skipped in %1.1fs.' % (
        success, len(failed), skipped, time.time() - start))
  return int(bool(remaining_masters or outstanding_expected or failed))


def main(argv):
  parser = optparse.OptionParser()
  parser.add_option('-v', '--verbose', action='count', default=0)
  options, args = parser.parse_args(argv[1:])
  if args:
    parser.error('Unknown args: %s' % args)
  levels = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)
  logging.basicConfig(level=levels[min(options.verbose, len(levels)-1)])

  # Remove site_config's we don't add ourselves. Can cause issues when running
  # this test under a buildbot-spawned process.
  sys.path = [x for x in sys.path if not x.endswith('site_config')]
  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  build_internal = os.path.join(os.path.dirname(base_dir), 'build_internal')
  sys.path.extend(os.path.normpath(os.path.join(base_dir, d)) for d in (
      'site_config',
      os.path.join(build_internal, 'site_config'),
  ))
  public_masters = {
      'master.chromium': 'Chromium',
      'master.chromium.chrome': 'ChromiumChrome',
      'master.chromium.chromedriver': 'ChromiumChromeDriver',
      'master.chromium.chromiumos': 'ChromiumChromiumOS',
      'master.chromium.endure': 'ChromiumEndure',
      'master.chromium.fyi': 'ChromiumFYI',
      'master.chromium.gatekeeper': 'Gatekeeper',
      'master.chromium.git': 'ChromiumGit',
      'master.chromium.gpu': 'ChromiumGPU',
      'master.chromium.gpu.fyi': 'ChromiumGPUFYI',
      'master.chromium.linux': 'ChromiumLinux',
      'master.chromium.lkgr': 'ChromiumLKGR',
      'master.chromium.mac': 'ChromiumMac',
      'master.chromium.memory': 'ChromiumMemory',
      'master.chromium.memory.fyi': 'ChromiumMemoryFYI',
      'master.chromium.perf': 'ChromiumPerf',
      'master.chromium.perf.fyi': 'ChromiumPerfFyi',
      'master.chromium.swarm': 'ChromiumSwarm',
      'master.chromium.webkit': 'ChromiumWebkit',
      'master.chromium.webrtc': 'ChromiumWebRTC',
      'master.chromium.webrtc.fyi': 'ChromiumWebRTCFYI',
      'master.chromium.win': 'ChromiumWin',
      'master.chromiumos': 'ChromiumOS',
      'master.chromiumos.chromium': 'ChromiumOSChromium',
      'master.chromiumos.tryserver': 'ChromiumOSTryServer',
      'master.client.dart': 'Dart',
      'master.client.dart.fyi': 'DartFYI',
      'master.client.dart.packages': 'DartPackages',
      'master.client.drmemory': 'DrMemory',
      'master.client.dynamorio': 'DynamoRIO',
      'master.client.libyuv': 'Libyuv',
      'master.client.libvpx': 'Libvpx',
      'master.client.nacl': 'NativeClient',
      'master.client.nacl.ports': 'NativeClientPorts',
      'master.client.nacl.ports.git': 'NativeClientPortsGit',
      'master.client.nacl.sdk': 'NativeClientSDK',
      'master.client.nacl.sdk.addin': 'NativeClientSDKAddIn',
      'master.client.nacl.sdk.mono': 'NativeClientSDKMono',
      'master.client.nacl.toolchain': 'NativeClientToolchain',
      'master.client.pagespeed': 'PageSpeed',
      'master.client.polymer': 'Polymer',
      'master.client.sfntly': 'Sfntly',
      'master.client.skia': 'Skia',
      'master.client.syzygy': 'Syzygy',
      'master.client.v8': 'V8',
      'master.client.v8.branches': 'V8Branches',
      'master.client.webrtc': 'WebRTC',
      'master.client.webrtc.fyi': 'WebRTCFYI',
      'master.experimental': 'Experimental',
      'master.push.canary': 'PushCanary',
      'master.tryserver.chromium': 'TryServer',
      'master.tryserver.chromium.linux': 'TryServerChromiumLinux',
      'master.tryserver.chromium.mac': 'TryServerChromiumMac',
      'master.tryserver.chromium.win': 'TryServerChromiumWin',
      'master.tryserver.chromium.gpu': 'GpuTryServer',
      'master.tryserver.chromium.perf': 'ChromiumPerfTryServer',
      'master.tryserver.blink': 'BlinkTryServer',
      'master.tryserver.libyuv': 'LibyuvTryServer',
      'master.tryserver.nacl': 'NativeClientTryServer',
      'master.tryserver.v8': 'V8TryServer',
      'master.tryserver.webrtc': 'WebRTCTryServer',
  }
  all_masters = { base_dir: public_masters }
  if os.path.exists(build_internal):
    internal_test_data = chromium_utils.ParsePythonCfg(
        os.path.join(build_internal, 'tests', 'internal_masters_cfg.py'),
        fail_hard=True)
    all_masters[build_internal] = internal_test_data['masters_test']
  return real_main(all_masters)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
