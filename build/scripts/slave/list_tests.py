#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import optparse
import os
import sys

def parse_args():
  parse = optparse.OptionParser()

  parse.add_option('--build_dir', default=os.getcwd())
  parse.add_option('-o', '--output_json',
                   help='Output JSON information into a specified file')
  return parse.parse_args()

def main():
  options, _ = parse_args()
  tests = {}
  execfile(os.path.join(options.build_dir,
    'src', 'build', 'android', 'pylib', 'gtest', 'gtest_config.py'), {}, tests)
  with open(options.output_json, 'wb') as f:
    f.write(json.dumps(tests))

if __name__ == '__main__':
  sys.exit(main())
