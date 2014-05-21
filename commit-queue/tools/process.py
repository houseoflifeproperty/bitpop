#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Analyse commits."""

import json
import logging
import optparse
import sys


def main():
  parser = optparse.OptionParser(
      description=sys.modules['__main__'].__doc__)
  parser.add_option('-v', '--verbose', action='store_true')
  options, args = parser.parse_args()
  if options.verbose:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.ERROR)
  if len(args) != 1:
    parser.error('Need 1 arg')

  data = json.load(open(args[0])) or {}
  revs = sorted(
      k for k, v in data.iteritems() if v['revprops'] and k != '24079')
  print '\n'.join(sorted(revs))
  return 0


if __name__ == '__main__':
  sys.exit(main())
