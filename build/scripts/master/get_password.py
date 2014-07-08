# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple password getter."""


class Password(object):
  def __init__(self, filename):
    self.filename = filename
    self.password = None

  def GetPassword(self):
    if not self.password:
      self.password = self.ForceGetPassword()
    return self.password

  def ForceGetPassword(self):
    password_file = open(self.filename, 'r')
    self.password = password_file.read().strip()
    password_file.close()
    return self.password

  def MaybeGetPassword(self, default=None):
    try:
      self.password = self.ForceGetPassword()
    except Exception as e:
      print e
      self.password = default
    return self.password
