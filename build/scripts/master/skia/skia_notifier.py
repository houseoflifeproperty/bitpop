# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Notifier classes for Skia build masters."""


from buildbot.status.mail import MailNotifier
from common.skia import builder_name_schema
from master.try_mail_notifier import TryMailNotifier


class SkiaMailNotifier(MailNotifier):
  """Filter out trybots from the MailNotifier."""
  def buildMessage(self, name, build, results):
    if not builder_name_schema.IsTrybot(build[0].getBuilder().name):
      return MailNotifier.buildMessage(self, name, build, results)


class SkiaTryMailNotifier(TryMailNotifier):
  """Filter out non-trybot builders from the TryMailNotifier."""
  def buildMessage(self, name, build, results):
    if builder_name_schema.IsTrybot(build[0].getBuilder().name):
      return TryMailNotifier.buildMessage(self, name, build, results)

