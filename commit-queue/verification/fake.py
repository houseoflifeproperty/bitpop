# coding=utf8
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A verifier that does nothing."""

from verification import base


class FakeVerifier(base.Verifier):
  name = 'fake'

  def __init__(self, state):
    super(FakeVerifier, self).__init__()
    self.state = state

  def verify(self, pending):
    pending.verifications[self.name] = base.SimpleStatus(self.state)

  def update_status(self, queue):
    pass


class DeferredFakeVerifier(base.Verifier):
  name = 'fake'

  def __init__(self, state):
    super(DeferredFakeVerifier, self).__init__()
    self.state = state

  def verify(self, pending):
    pending.verifications[self.name] = base.SimpleStatus()

  def update_status(self, queue):
    for _, fake in self.loop(queue, base.SimpleStatus, True):
      fake.state = self.state
