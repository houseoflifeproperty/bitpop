# coding=utf8
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Runs presubmit check on the source tree."""

import logging
import os
import sys
import time

from verification import base

import find_depot_tools  # pylint: disable=W0611
import subprocess2


class PresubmitCheckVerifier(base.VerifierCheckout):
  name = 'presubmit'

  def __init__(self, context_obj, timeout=6*60):
    super(PresubmitCheckVerifier, self).__init__(context_obj)
    self.root_dir = os.path.dirname(os.path.abspath(__file__))
    self.execution_timeout = timeout

  def verify(self, pending):
    """Runs the presubmit script synchronously.

    TODO(maruel): Now that it runs out of process, it should be run
    asynchronously. That means that the PRESUBMIT checks needs to be better
    written, if an integration tests starts a service, it needs to be able to
    use an ephemeral port and not an hardcoded port.
    """
    logging.info('Presubmit check for %s' % ','.join(pending.files))
    cmd = [
        sys.executable,
        os.path.join(self.root_dir, 'presubmit_shim.py'),
        '--commit',
        '--author', str(pending.owner),
        '--issue', str(pending.issue),
        '--patchset', str(pending.patchset),
        '--name', pending.pending_name(),
        '--description', pending.description,
        '--rietveld_url', self.context.rietveld.url,
    ]
    if logging.getLogger().isEnabledFor(logging.DEBUG):
      cmd.append('--verbose')
    cmd.extend(pending.files)
    start = time.time()
    self.send_status(pending, {})

    # Disable breakpad, no need to notify maintainers on internal crashes.
    env = os.environ.copy()
    env['NO_BREAKPAD'] = '1'

    try:
      # Do not pass them through the command line.
      data = '%s\n%s\n' % (
          self.context.rietveld.email, self.context.rietveld.password)
      # Use check_output() so stdout is kept when an exception is thrown.
      output = subprocess2.check_output(
          cmd,
          timeout=self.execution_timeout,
          stderr=subprocess2.STDOUT,
          stdin=data,
          env=env)
      pending.verifications[self.name] = base.SimpleStatus(state=base.SUCCEEDED)
      self.send_status(
          pending,
          {
            'duration': time.time() - start,
            'output': output,
          })
    except subprocess2.CalledProcessError, e:
      output = (
          'Presubmit check for %s failed and returned exit status %s.\n') % (
              pending.pending_name(), e.returncode)
      duration = time.time() - start
      timed_out = duration > self.execution_timeout
      if timed_out:
        output += (
            'The presubmit check was hung. It took %2.1f seconds to execute '
            'and the time limit is %2.1f seconds.\n') % (
                duration, self.execution_timeout)
      output += '\n%s' % e.stdout
      pending.verifications[self.name] = base.SimpleStatus(
          state=base.FAILED, error_message=output)
      self.send_status(
          pending,
          {
            'duration': duration,
            'output': e.stdout,
            'return': e.returncode,
            'timed_out': timed_out,
          })

  def update_status(self, queue):
    pass
