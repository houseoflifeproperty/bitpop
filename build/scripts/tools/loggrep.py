#!/usr/bin/python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Searches for a regular expression in log messages.

Unlike simple grep preserves multiline logs and unlike sort preserves order of
the log messages having the same timestamp.
"""

import operator
import re
import sys


TIMESTAMP_REGEXP = r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d-\d\d\d\d'


def main():
  if len(sys.argv) == 1 or sys.argv[1] == '--help':
    print 'Usage: loggrep.py search_regexp [log_files...]'
    return

  search_regexp = sys.argv[1]
  log_files = sys.argv[2:]

  # Read all log lines.
  log_lines = []
  for filename in log_files:
    log_lines.extend(open(filename).readlines())

  # Extract log messages from the lines.
  timestamp_pattern = re.compile(TIMESTAMP_REGEXP)
  log_messages = []
  message_lines = []
  for line in log_lines:
    if timestamp_pattern.match(line):
      if message_lines:
        log_messages.append(''.join(message_lines))
      message_lines = [line]
    else:
      message_lines.append(line)
  if message_lines:
    log_messages.append(''.join(message_lines))

  # Filter out log messages not matching the search query.
  search_pattern = re.compile(search_regexp)
  filtered_messages = [message for message in log_messages
                               if search_pattern.search(message)]

  # Group and sort messages by timestamp preserving their sequential order in
  # each group.
  grouped_messages = {}
  for message in filtered_messages:
    timestamp = timestamp_pattern.match(message).group(0)
    grouped_messages.setdefault(timestamp, [])
    grouped_messages[timestamp].append(message)
  grouped_messages = sorted(grouped_messages.items(),
                            key=operator.itemgetter(0))

  # Print out all messages.
  for _, message_group in grouped_messages:
    for message in message_group:
      print message,


if __name__ == '__main__':
  sys.exit(main())