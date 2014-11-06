#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive build dependencie data, which is used by
   http://blame-bot.appspot.com to find culprit CLs for regressions.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import gzip
import optparse
import os
import shutil
import subprocess
import sys
import tempfile

from slave import slave_utils


def _RunNinjaSubTool(options, tmp_dir, sub_tool):
  ninja_dir = os.path.join('out', options.target)
  command = ['ninja', '-C', ninja_dir, '-t', sub_tool]
  filename = 'ninja-%s.txt' % sub_tool
  txt = os.path.join(tmp_dir, filename)
  with open(txt, 'w') as f:
    print 'Running command %s, saving output to %s' % (command, txt)
    retcode = subprocess.call(command, stdout=f)
    print 'Command returned %d' % retcode
  with open(txt) as f:
    txt_gz = txt + '.gz'
    with gzip.open(txt_gz, 'w') as g:
      g.writelines(f)

  upload_url = 'gs://blame-bot.appspot.com/%s/%s/%s' % (options.master,
      options.builder, options.build)
  slave_utils.GSUtilCopyFile(txt_gz, upload_url)


def Archive(options, args):
  try:
    start_dir = os.getcwd()
    print 'Changing directory to %s' % options.src_dir
    os.chdir(options.src_dir)
    try:
      tmp_dir = tempfile.mkdtemp()
      print 'Staging in %s' % tmp_dir
      _RunNinjaSubTool(options, tmp_dir, 'graph')
      _RunNinjaSubTool(options, tmp_dir, 'deps')
    finally:
      os.chdir(start_dir)
  finally:
    shutil.rmtree(tmp_dir)


def main():
  option_parser = optparse.OptionParser()

  option_parser.add_option('--src-dir', default='src',
                           help='path to the root of the source tree')
  option_parser.add_option('--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('--master', help='master name (e.g. chromium)')
  option_parser.add_option('--builder', help='builder name (e.g. Linux)')
  option_parser.add_option('--build', help='build number (e.g. 53197)')

  options, args = option_parser.parse_args()

  options.src_dir = os.path.abspath(options.src_dir)

  if not options.master or not options.builder or not options.build:
    print option_parser.usage
    return 1

  return Archive(options, args)


if __name__ == '__main__':
  sys.exit(main())
