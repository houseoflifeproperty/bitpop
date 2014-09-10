# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import logging
import os
import time

from logging.handlers import TimedRotatingFileHandler

from buildbot.status.base import StatusReceiverMultiService


class StatusEventLogger(StatusReceiverMultiService):
  """Logs all status events to a file on disk. Uses a rotating file log."""
  def __init__(self, logfile='status.log'):
    """Create a StatusEventLogger.

    Args:
      logfile: base filename for events to be written to.
    """
    self.logfile = logfile
    # Will be initialized in startService
    self.logger = None
    self.status = None
    self._active = False
    self._last_checked_active = 0
    # Can't use super because StatusReceiverMultiService is an old-style class.
    StatusReceiverMultiService.__init__(self)

  @property
  def active(self):
    now = time.time()
    # Cache the value for self._active for one minute.
    if now - self._last_checked_active > 60:
      self._active = os.path.isfile(
          os.path.join(self.parent.basedir, '.logstatus'))
      self._last_checked_active = now
    return self._active

  def startService(self):
    """Start the service and subscribe for updates."""
    logger = logging.getLogger(__name__)
    logger.propagate = False
    logger.setLevel(logging.INFO)
    # %(bbEvent)19s because builderChangedState is 19 characters long
    formatter = logging.Formatter('%(asctime)s - %(bbEvent)19s - %(message)s')
    # Use delay=True so we don't open an empty file while self.active=False.
    handler = TimedRotatingFileHandler(
        os.path.join(self.parent.basedir, self.logfile),
        when='H', interval=1, delay=True)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    self.logger = logger

    StatusReceiverMultiService.startService(self)
    self.status = self.parent.getStatus()
    self.status.subscribe(self)

  def log(self, event, message, *args):
    """Simple wrapper for log. Passes string formatting args through."""
    if self.active:
      self.logger.info(message, *args, extra={'bbEvent': event})

  def requestSubmitted(self, request):
    builderName = request.getBuilderName()
    self.log('requestSubmitted', '%s, %r', builderName, request)

  def requestCancelled(self, builder, request):
    builderName = builder.getName()
    self.log('requestCancelled', '%s, %r', builderName, request)

  def buildsetSubmitted(self, buildset):
    reason = buildset.getReason()
    self.log('buildsetSubmitted', '%r, %s', buildset, reason)

  def builderAdded(self, builderName, builder):
    # Use slavenames rather than getSlaves() to just get strings.
    slaves = builder.slavenames
    self.log('builderAdded', '%s, %r', builderName, slaves)
    # Must return self in order to subscribe to builderChangedState and
    # buildStarted/Finished events.
    return self

  def builderChangedState(self, builderName, state):
    self.log('builderChangedState', '%s, %r', builderName, state)

  def buildStarted(self, builderName, build):
    build_number = build.getNumber()
    slave = build.getSlavename()
    self.log('buildStarted', '%s, %d, %s', builderName, build_number, slave)
    # Must return self in order to subscribe to stepStarted/Finished events.
    return self

  def buildETAUpdate(self, build, ETA):
    # We don't actually care about ETA updates; they happen on a periodic clock.
    pass

  def changeAdded(self, change):
    self.log('changeAdded', '%r', change)

  def stepStarted(self, build, step):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepStarted', '%s, %d, %s', build_name, build_number, step_name)
    # Must return self in order to subscribe to logStarted/Finished events.
    return self

  def stepTextChanged(self, build, step, text):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepTextChanged', '%s, %d, %s, %s',
             build_name, build_number, step_name, text)

  def stepText2Changed(self, build, step, text2):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepText2Changed', '%s, %d, %s, %s',
             build_name, build_number, step_name, text2)

  def stepETAUpdate(self, build, step, ETA, expectations):
    # We don't actually care about ETA updates; they happen on a periodic clock.
    pass

  def logStarted(self, build, step, log):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    log_name = log.getName()
    log_file = log.filename
    self.log('logStarted', '%s, %d, %s, %s, %s',
             build_name, build_number, step_name, log_name, log_file)
    # Create an attr on the stateful log object to count its chunks.
    log.__num_chunks = 0
    # Must return self in order to subscribe to logChunk events.
    return self

  def logChunk(self, build, step, log, channel, text):
    # Like the NSA, we only want to process metadata.
    log.__num_chunks += 1

  def logFinished(self, build, step, log):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    log_name = log.getName()
    log_file = log.filename
    log_size = log.length
    # Access to protected member __num_chunks. pylint: disable=W0212
    log_chunks = log.__num_chunks
    self.log('logFinished', '%s, %d, %s, %s, %s, %d, %d',
             build_name, build_number, step_name,
             log_name, log_file, log_size, log_chunks)

  def stepFinished(self, build, step, results):
    build_name = build.getBuilder().name
    build_number = build.getNumber()
    step_name = step.getName()
    self.log('stepFinished', '%s, %d, %s, %r',
             build_name, build_number, step_name, results)

  def buildFinished(self, builderName, build, results):
    build_number = build.getNumber()
    slave = build.getSlavename()
    self.log('buildFinished', '%s, %d, %s, %r',
             builderName, build_number, slave, results)

  def builderRemoved(self, builderName):
    self.log('builderRemoved', '%s', builderName)

  def slaveConnected(self, slaveName):
    self.log('slaveConnected', '%s', slaveName)

  def slaveDisconnected(self, slaveName):
    self.log('slaveDisconnected', '%s', slaveName)
