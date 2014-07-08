#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Lists slaves with hung build steps."""

import logging
import os
import optparse
import re
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '..'))
sys.path.append(os.path.join(BASE_DIR, '..', '..', '..', 'commit-queue'))

import buildbot_json  # pylint: disable=F0401
from tools import slaves


def format_time(value):
  """Convert a value in seconds into a human readable string."""
  out = ''
  value = int(value)
  for divider, unit_name in ((60, 's'), (60, 'm'), (24, 'h'), (0, 'd')):
    value, unit = divmod(value, divider) if divider else (0, value)
    out = '%02d%s%s' % (unit, unit_name, out)
    if not value:
      break
  return re.sub(r'^0(\d)', r'\1', out)


def from_time(value):
  """Convert a human readable string representing a duration into a int as
  seconds.

  This function considers 2m1h4d a valid string for simplicity.
  """
  units = {'d': 24*60*60, 'h': 60*60, 'm': 60, 's': 1, '': 1}
  return sum(
      int(x) * units[unit]
      for x, unit in re.findall(r'(\d+)(d|h|m|s|)', value))


def main():
  usage = """%prog [options] <master>

Sample usage:
  %prog t.c -d 3h

Note: t is replaced with 'tryserver', 'c' with chromium' and
      co with 'chromiumos'.

Only the slave names are printed on stdout, making it bash-friendly.
"""
  parser = optparse.OptionParser(usage=usage)
  parser.add_option(
      '-b', '--builder',
      action='append',
      default=[],
      help='Specify builders (use multiple times), otherwise selects all')
  parser.add_option(
      '-d', '--duration',
      help='Only builds of specific duration or more, formated')
  parser.add_option('-v', '--verbose', action='count', default=0)
  options, args = parser.parse_args()

  if len(args) != 1:
    parser.error('Unsupported args %s' % ' '.join(args))

  levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
  logging.basicConfig(level=levels[min(len(levels)-1, options.verbose)])

  url = 'http://build.chromium.org/p/%s' % slaves.ProcessShortName(args[0])
  buildbot = buildbot_json.Buildbot(url)
  if options.builder:
    builders = [buildbot.builders[b] for b in options.builder]
  else:
    builders = buildbot.builders

  if options.duration:
    options.duration = from_time(options.duration)

  now = time.time()
  for builder in builders:
    for build in builder.current_builds:
      start, end = build.data['times']
      if end:
        continue
      duration = now - start
      if not options.duration or duration > options.duration:
        print build.slave.name
        logging.warn('%s(%d) elapsed:%s' % (
            builder.name, build.number,
            format_time(duration)))


if __name__ == '__main__':
  sys.exit(main())
