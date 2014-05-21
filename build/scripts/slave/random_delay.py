#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to sleep for a random amount of time, used by the buildbot slaves.

  This is used to prevent the cron - zerg rush/herd stampede/feeding frenzy
  of large numbers of builders starting synchronously.
  One can imagine other uses for the same process.
"""

import optparse
import random
import sys
import time


def main():

  option_parser = optparse.OptionParser(usage=
      """%prog [options]

Do nothing for a (pseudo)random amount of time.

Sample Usage:
  %prog --max 30 # sleep for less than about a half minute.
  %prog --min 60 --max 120 # ... between a minute and two minutes.
  %prog -q  # Do it without telling us how long, or when it's done.""")

  option_parser.add_option('--max', default=10, type='int',
                           help='Maximum number of seconds to sleep')
  option_parser.add_option('--min', default=1, type='int',
                           help='Minimum number of seconds to sleep')
  option_parser.add_option('-q', '--quiet', dest='verbose',
      action='store_false')
  option_parser.add_option('-v', '--verbose', action='store_true', default=True)

  options, args = option_parser.parse_args()

  if args:
    option_parser.error("Found parameters I don't understand: %r" % args)

  delay = random.randrange(options.min * 100, options.max * 100) / 100.0

  if options.verbose:
    print "Sleeping for %.2F seconds ..." % delay

  try:
    time.sleep(delay)
  except EnvironmentError:
    if options.verbose:
      print "... failed."
      sys.stdout.flush()
    raise
  except KeyboardInterrupt:
    if options.verbose:
      print "... stopped."
  else:
    if options.verbose:
      print "... done."


if '__main__' == __name__:
  sys.exit(main())
