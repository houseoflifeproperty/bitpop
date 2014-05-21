# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Retrieve the list of the current build sheriffs."""

import datetime
import os
import re


class BuildSheriffs(object):
  # File that contains the string containing the build sheriff names.
  # Note: Don't pull from http because if it ever come back to BB, it will
  # hang since BB web server is not reentrant!
  sheriff_file_pattern_ = '%s.js'

  # RE to retrieve the sheriff names.
  usernames_matcher_ = re.compile(r'document.write\(\'([\w, ]+)\'\)')

  # The datetime when the named sheriff cache expires.
  good_until_ = {}
  # Cached Sheriffs list.
  sheriffs_ = {}

  @staticmethod
  def GetSheriffs(classes, data_dir='public_html'):
    """Returns a list of build sheriffs for the current week."""
    # Update ten times per hour
    now = datetime.datetime.utcnow()
    sheriffs = []

    for name in classes:
      if name not in BuildSheriffs.good_until_ or (
          BuildSheriffs.good_until_[name] < now):
        BuildSheriffs.good_until_[name] = now + datetime.timedelta(minutes=6)
        # Initialize in case nothing is found.
        BuildSheriffs.sheriffs_[name] = []
        sheriff_file = os.path.join(data_dir,
                                    BuildSheriffs.sheriff_file_pattern_ % name)
        if os.path.isfile(sheriff_file):
          try:
            f = open(sheriff_file, 'r')
            line = f.readlines()[0]
            f.close()
            usernames_match = BuildSheriffs.usernames_matcher_.match(line)
            if usernames_match:
              usernames_str = usernames_match.group(1)
              if usernames_str != 'None (channel is sheriff)':
                for sheriff in usernames_str.split(', '):
                  if sheriff.count('@') == 0:
                    sheriff += '@google.com'
                  BuildSheriffs.sheriffs_[name].append(sheriff)
          except (IOError, ValueError):
            BuildSheriffs.good_until_[name] = (now +
                datetime.timedelta(minutes=2))

      sheriffs.extend(BuildSheriffs.sheriffs_[name])

    return sheriffs
