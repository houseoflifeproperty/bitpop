# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Loads credentials."""

import os

import errors


class Credentials(object):
  """Keeps a dictionary of accounts."""

  def __init__(self, pwd_path):
    try:
      content = open(pwd_path, 'r').read()
    except IOError:
      raise errors.ConfigurationError(
          '%s is missing. Please read workdir/README.' %
              os.path.basename(pwd_path))
    lines = [l.strip() for l in content.splitlines()]
    lines = [l for l in lines if l and not l.startswith('#')]
    self.creds = {}
    for l in lines:
      items = l.split(':', 1)
      self.creds[items[0].strip()] = items[1].strip()

  def get(self, user):
    return self.creds.get(user, None)
