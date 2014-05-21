#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Watch for rietveld issues with the commit bit set but no activity."""

import datetime
import logging
import optparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import find_depot_tools  # pylint: disable=W0611
import breakpad
import rietveld


def seconds(td):
  return td.seconds + td.days * 24 * 3600


def to_epoch(date_str):
  dt = datetime.datetime(*map(int, re.split('[^\d]', date_str)[:-1]))
  return seconds(dt - datetime.datetime(1970, 1, 1))


def main():
  parser = optparse.OptionParser(
      description=sys.modules['__main__'].__doc__)
  parser.add_option('-d', '--delay', default=3*60*60, type='int')
  parser.add_option('-u', '--user')
  parser.add_option('-v', '--verbose', action='store_true')
  options, args = parser.parse_args()
  if options.verbose:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.ERROR)
  if len(args) != 1:
    parser.error('Need 1 arg')

  url = args[0].rstrip('/') + '/'
  if not 'http' in url:
    url = 'http://' + url
  obj = rietveld.Rietveld(args[0], options.user, None)
  notified = []
  while True:
    now = time.time()
    earliest = now - options.delay
    for issue in obj.search(commit='1', closed='2'):
      print '%d' % issue['issue']
      if issue['issue'] in notified:
        continue
      if (not issue['base_url'] or
          to_epoch(issue['modified']) < earliest):
        data = ['%s%d' % (url, issue['issue']), issue['base_url']]
        breakpad.SendStack(str(now), data)
        notified.append(issue['issue'])
    time.sleep(5*60)
  return 0


if __name__ == '__main__':
  sys.exit(main())
