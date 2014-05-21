#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A small maintenance tool to do quiet test state creation on test masters."""

import os
import optparse
import sys
import sqlite3
import time


def dump(from_db_filename, to_txt_filename):
  connection = sqlite3.connect(from_db_filename)
  with open(to_txt_filename, 'w') as txt_file:
    for line in connection.iterdump():
      txt_file.write('%s\n' % line)


def restore(from_txt_filename, to_db_filename):

  with open(from_txt_filename, 'r') as txt_file:
    try:
      os.remove(to_db_filename)
    except OSError as err:
      if err.errno != 2:
        raise
    connection = sqlite3.connect(to_db_filename)
    cursor = connection.cursor()
    cursor.executescript(txt_file.read())
    cursor.close()


def Main(argv):
  usage = """%prog [options]

Copy a database to and/or from a text file SQL description.
By default, nothing happens, and when both are specified, the
dump direction comes first (the database is essentially rebuilt).

Sample usage:
  %prog --dump
  %prog --restore
  %prog --dump --db master.chromium/state.sqlite --txt=template.txt
  %prog --dump --restore --yes # see omphaloskepsis
"""

  parser = optparse.OptionParser(usage=usage)
  parser.add_option('--dump', action='store_true',
      help='copy from database to text file')
  parser.add_option('--restore', action='store_true',
      help='copy from text file to database')
  parser.add_option('--yes', action='store_true')
  parser.add_option('--db', default='state.sqlite',
      help='sqlite database name')
  parser.add_option('--txt', default='../state-template.txt',
      help='filename for text dump')
  options, args = parser.parse_args(argv)

  if args:
    parser.error("Found parameters I don't understand: %r" % args)
  if options.dump and options.restore:
    print 'Both a dump and a restore.  Fun.  Hope you meant it.'
    print 'Will dump first.'
    if not options.yes:
      time.sleep(3.14)

  if not options.dump and not options.restore:
    print 'Neither a dump nor a restore.  Boring.'

  if options.dump:
    dump(options.db, options.txt)

  if options.restore:
    restore(options.txt, options.db)


if __name__ == '__main__':
  sys.exit(Main(None))
