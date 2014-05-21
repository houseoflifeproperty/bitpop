# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from master import chromium_notifier


class PerfNotifier(chromium_notifier.ChromiumNotifier):
  """This is a status notifier which alerts on perf changes.

  See builder.interfaces.IStatusReceiver to have more information about the
  parameters type."""

  def __init__(self, **kwargs):
    chromium_notifier.ChromiumNotifier.__init__(self, **kwargs)

  def stepFinished(self, build, step, results):
    """A build step has just finished.

    Wraps ChromiumNotifier.stepFinished() to check if step contains a regress
    or improve message.  Returns early if it does not."""
    if not re.match(r'.*PERF_(REGRESS|IMPROVE).*', ' '.join(step.getText())):
      return

    return chromium_notifier.ChromiumNotifier.stepFinished(
        self, build, step, results)
