#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0403,W0611

import unittest

from slave import chromium_commands


class ChromiumCommandsTest(unittest.TestCase):
  def test_extract_revisions_empty(self):
    data = ''
    expected = {}
    actual = chromium_commands.extract_revisions(data)
    self.assertEqual(expected, actual)

  def test_extract_revisions_short(self):
    data = (
      '124>_____ src/tools/swarming_client at '
        'c60aabe2367cea6a9cdecd895a9da5a0a381201d\n'
      '124>________ running \'git ...\' in \'/build\'\n'
      '124>Cloning into \'/build/src/tools/_gclient_swarming_client_LfrCWh\'...'
        '\n'
      '124>POST git-upload-pack (174 bytes)\n'
      '124>remote: Total 2041 (delta 1534), reused 2041 (delta 1534)\n'
      '124>Receiving objects: 100% (2041/2041)\n'
      '124>Receiving objects: 100% (2041/2041), 619.13 KiB | 0 bytes/s, done.\n'
      '124>Resolving deltas: 100% (1534/1534)\n'
      '124>Resolving deltas: 100% (1534/1534), done.\n'
      '124>Checking connectivity... done\n'
      '124>________ running \'git checkout --quiet '
        'c60aabe2367cea6a9cdecd895a9da5a0a381201d\' in '
        '\'/build/src/tools/swarming_client\'\n'
      '124>Checked out c60aabe2367cea6a9cdecd895a9da5a0a381201d to a detached '
        'HEAD. Before making any commits\n'
      '124>in this repo, you should use \'git checkout <branch>\' to switch to'
        '\n'
      '124>an existing branch or use \'git checkout origin -b <branch>\' to\n'
      '124>create a new branch for your work.\n')
    expected = {
      'got_revision': 'c60aabe2367cea6a9cdecd895a9da5a0a381201d',
      'got_swarming_client_revision':
        'c60aabe2367cea6a9cdecd895a9da5a0a381201d',
    }
    actual = chromium_commands.extract_revisions(data)
    self.assertEqual(expected, actual)


if __name__ == '__main__':
  unittest.main()
