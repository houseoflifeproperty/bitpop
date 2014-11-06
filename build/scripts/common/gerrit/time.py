# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of Gerrit time-manipulation functions."""

import datetime


GERRIT_TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'


def ParseGerritTime(value):
  """Parses a Gerrit-formatted timestamp into a Python 'datetime'.
  From Gerrit API documentation:
    `Timestamps are given in UTC and have the format
    "yyyy-mm-dd hh:mm:ss.fffffffff" where "ffffffffff" indicates the
    nanoseconds.`

  Args:
    value: (str) the value to parse

  Return: A Python 'datetime' object parsed from 'value'
  """
  parts = value.split('.')
  dt = datetime.datetime.strptime(parts[0], GERRIT_TIMESTAMP_FMT)
  if len(parts) > 1:
    dt += datetime.timedelta(
        microseconds=int(float('0.%s' % parts[1]) * 1000000.0))
  return dt


def ToGerritTime(value):
  """Converts a Python 'datetime' to a Gerrit-formatted timestamp. See
  'ParseGerritTime' for details.

  Args:
    value: (datetime.datetime) the value to convert
  Return: A Gerrit timestamp string
  """
  # Get nanoseconds (<= 10 characters)
  ns_str = str(value.microsecond * 1000)

  return '%s.%s' % (
      value.strftime(GERRIT_TIMESTAMP_FMT),
      ns_str)
