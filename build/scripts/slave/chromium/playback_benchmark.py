#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to run the playback tests, used by the buildbot slaves.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import logging
import optparse
import os
import shutil
import simplejson as json
import subprocess
import sys
import tempfile
import threading

from common import chromium_utils
from slave import xvfb
from slave.chromium import playback_benchmark_replay

# So we can import google.*_utils below with native Pythons.
sys.path.append(os.path.abspath('src/tools/python'))

USAGE = '%s [options]' % os.path.basename(sys.argv[0])

SERVER_PORT = 8080
START_URL = 'http://localhost:%i' % SERVER_PORT

def print_result(top, name, result, refbuild):
  prefix = ''
  if top:
    prefix = '*'
  score_label = 'score'
  if refbuild:
    score_label = 'score_ref'
  print ('%sRESULT %s: %s= %s ms (smaller is better)' %
         (prefix, name, score_label, str(result)))


def run_benchmark(options, use_refbuild, benchmark_results):
  result = 0

  build_dir = os.path.abspath(options.build_dir)
  if not use_refbuild:
    if chromium_utils.IsMac():
      build_dir = os.path.join(os.path.dirname(build_dir), 'xcodebuild')
    elif chromium_utils.IsLinux():
      build_dir = os.path.join(os.path.dirname(build_dir), 'sconsbuild')
    build_dir = os.path.join(build_dir, options.target)
  else:
    build_dir = os.path.join(os.path.dirname(build_dir), 'chrome', 'tools',
                             'test', 'reference_build')
    if chromium_utils.IsMac():
      build_dir = os.path.join(build_dir, 'chrome_mac')
    elif chromium_utils.IsLinux():
      build_dir = os.path.join(build_dir, 'chrome_linux')
    else:
      build_dir = os.path.join(build_dir, 'chrome_win')

  if chromium_utils.IsWindows():
    chrome_exe_name = 'chrome.exe'
  elif chromium_utils.IsLinux():
    chrome_exe_name = 'chrome'
  else:
    chrome_exe_name = 'Chromium'
  chrome_exe_path = os.path.join(build_dir, chrome_exe_name)
  if not os.path.exists(chrome_exe_path):
    raise chromium_utils.PathNotFound('Unable to find %s' % chrome_exe_path)

  temp_dir = tempfile.mkdtemp()
  command = [chrome_exe_path,
             '--user-data-dir=%s' % temp_dir,
             '--no-first-run',
             '--no-default-browser-check',
             START_URL]

  print "Executing: "
  print command
  browser_process = subprocess.Popen(command)

  benchmark_results['ready'].wait()
  if benchmark_results['ready'].isSet():
    results = json.loads(benchmark_results['results'])[0]
    print_result(True, 'Total', results['score'], use_refbuild)
    for child in results['children']:
      print_result(False, child['name'], child['score'], use_refbuild)
  benchmark_results['ready'].clear()

  if chromium_utils.IsWindows():
    subprocess.call('taskkill /f /pid %i /t' % browser_process.pid)
  else:
    os.system('kill -15 %i' % browser_process.pid)
  browser_process.wait()
  shutil.rmtree(temp_dir)
  return result


def playback_benchmark(options, args):
  """Using the target build configuration, run the playback test."""
  root_dir = os.path.dirname(options.build_dir) # That's src dir.
  data_dir = os.path.join(root_dir, 'data', 'webapp_benchmarks', 'gmailjs')

  benchmark_results = {'ready': threading.Event()}
  def callback(results):
    benchmark_results['results'] = results
    benchmark_results['ready'].set()

  benchmark = playback_benchmark_replay.ReplayBenchmark(callback,
                                                        data_dir,
                                                        SERVER_PORT)
  server_thread = threading.Thread(target=benchmark.RunForever)
  server_thread.setDaemon(True)
  server_thread.start()

  if chromium_utils.IsLinux():
    xvfb.StartVirtualX(options.target, '')

  result = run_benchmark(options, False, benchmark_results)
  result |= run_benchmark(options, True, benchmark_results)

  if chromium_utils.IsLinux():
    xvfb.StopVirtualX(options.target)

  return result


def main():
  # Initialize logging.
  log_level = logging.INFO
  logging.basicConfig(level=log_level,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')

  option_parser = optparse.OptionParser(usage=USAGE)

  option_parser.add_option('', '--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('', '--build-dir', default='chrome',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  options, args = option_parser.parse_args()
  return playback_benchmark(options, args)


if '__main__' == __name__:
  sys.exit(main())
