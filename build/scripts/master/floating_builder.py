# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from datetime import datetime

from twisted.python import log
from twisted.internet import reactor

class PokeBuilderTimer(object):
  def __init__(self, botmaster, buildername):
    self.botmaster = botmaster
    self.buildername = buildername
    self.delayed_call = None

  def cancel(self):
    if self.delayed_call is not None:
      self.delayed_call.cancel()
      self.delayed_call = None

  def reset(self, delta):
    if self.delayed_call is not None:
      current_delta = (datetime.fromtimestamp(self.delayed_call.getTime()) -
                       datetime.datetime.now())
      if delta < current_delta:
        self.delayed_call.reset(delta.total_seconds())
      return

    # Schedule a new call
    self.delayed_call = reactor.callLater(
        delta.total_seconds(),
        self._poke,
    )

  def _poke(self):
    self.delayed_call = None
    log.msg("Poking builds for builder %r" % (self.buildername,))
    self.botmaster.maybeStartBuildsForBuilder(self.buildername)


class FloatingNextSlaveFunc(object):
  """
  This object, when used as a Builder's 'nextSlave' function, allows a strata-
  based preferential treatment to be assigned to a Builder's Slaves.

  The 'nextSlave' function is called on a scheduled build when an associated
  slave becomes available, either coming online or finishing an existing build.
  These events are used as stimulus to enable the primary builder(s) to pick
  up builds when appropriate.

  1) If a Primary is available, the build will be assigned to them.
  2) If a Primary builder is busy or is still within its grace period for
    unavailability, no slave will be assigned in anticipation of the
    'nextSlave' being re-invoked once the builder returns (1). If the grace
    period expires, we "poke" the master to call 'nextSlave', at which point
    the build will fall through to a lower strata.
  3) If a Primary slave is offline past its grace period, the build will be
    assigned to a Floating slave.

  Args:
    strata_property: (str) The name of the Builder property to use to identify
        its strata.
    strata: (list) A list of strata values ordered by selection priority
    grace_period: (None/timedelta) If not None, the amount of time that a slave
        can be offline before builds fall through to a lower strata.
  """

  def __init__(self, strata_property, strata, grace_period=None):
    self._strata = tuple(strata)
    self._strata_property = strata_property
    self._grace_period = grace_period
    self._slave_strata_map = {}
    self._slave_seen_times = {}
    self._poke_builder_timers = {}
    self.verbose = False

  def __repr__(self):
    return '%s(%s)' % (type(self).__name__, ' > '.join(self._strata))

  def __call__(self, builder, slave_builders):
    """Main 'nextSlave' invocation point.

    When this is called, we are given the following information:
    - The Builder
    - A set of 'SlaveBuilder' instances that are available and ready for
      assignment (slave_builders).
    - The total set of ONLINE 'SlaveBuilder' instances associated with
      'builder' (builder.slaves)
    - The set of all slaves configured for Builder (via
      '_get_all_slave_status')

    We compile that into a stateful awareness and use it as a decision point.
    Based on the slave availability and grace period, we will either:
    (1) Return a slave immediately to claim this build
    (2) Return 'None' (delaying the build) in anticipation of a higher-strata
        slave becoming available.

    If we go with (2), we will schedule a 'poke' timer to stimulate a future
    'nextSlave' call if the only higher-strata slave candidates are currently
    offline. We do this because they could be permanently offline, so there's
    no guarentee that a 'nextSlave' will be naturally called in any time frame.
    """
    self._debug("Calling %r with builder=[%s], slaves=[%s]",
                self, builder, slave_builders)
    self._cancel_builder_timer(builder)

    # Get the set of all 'SlaveStatus' assigned to this Builder (idle, busy,
    # and offline).
    slave_status_map = dict(
        (slave_status.name, slave_status)
        for slave_status in self._get_all_slave_status(builder)
    )

    # Index proposed 'nextSlave' slaves by name
    proposed_slave_builder_map = {}
    for slave_builder in slave_builders:
      proposed_slave_builder_map[slave_builder.slave.slavename] = slave_builder

    # Calculate the oldest a slave can be before we assume something's wrong.
    grace_threshold = now = None
    if self._grace_period is not None:
      now = datetime.now()
      grace_threshold = (now - self._grace_period)

    # Index all builder slaves (even busy ones) by name. Also, record this
    # slave's strata so we can reference it even if the slave goes offline
    # in the future.
    online_slave_builders = set()
    for slave_builder in builder.slaves:
      build_slave = slave_builder.slave
      if build_slave is None:
        continue
      self._record_strata(build_slave)
      if now is not None:
        self._record_slave_seen_time(build_slave, now)
      online_slave_builders.add(build_slave.slavename)

    # Check the strata, in order.
    for stratum in self._strata:
      busy_slaves = []
      offline_slaves = []
      wait_delta = None

      for slave_name in self._slave_strata_map.get(stratum, ()):
        self._debug("Considering slave %r for stratum %r", slave_name, stratum)

        # Get the 'SlaveStatus' object for this slave
        slave_status = slave_status_map.get(slave_name)
        if slave_status is None:
          continue

        # Was this slave proposed by 'nextSlave'?
        slave_builder = proposed_slave_builder_map.get(slave_name)
        if slave_builder is not None:
          # Yes. Use it!
          self._debug("Slave %r is available", slave_name)
          return slave_builder

        # Is this slave online?
        if slave_name in online_slave_builders:
          # The slave is online, but is not proposed (BUSY); add it to the
          # desired slaves list.
          self._debug("Slave %r is online but BUSY; marking preferred",
                      slave_name)
          busy_slaves.append(slave_name)
          continue

        # The slave is offline; do we have a grace period?
        if grace_threshold is None:
          # No grace period, so this slave is not a candidate
          self._debug("Slave %r is OFFLINE with no grace period; ignoring",
                      slave_name)
          continue

        # Yes; is this slave within the grace period?
        last_seen = self._get_latest_seen_time(slave_status)
        if last_seen < grace_threshold:
          # Not within grace period, so this slave is out.
          self._debug("Slave %r is OFFLINE and outside of grace period "
                      "(%s < %s); ignoring",
                      slave_name, last_seen, grace_threshold)
          continue

        # This slave is within its grace threshold. Add it to the list of
        # desired stratum slaves and update our wait delta in case we have to
        # poke.
        #
        # We track the longest grace period delta, since after this point if
        # no slaves have taken the build we would otherwise hang.
        self._debug("Slave %r is OFFLINE but within grace period "
                    "(%s >= %s); marking preferred",
                    slave_name, last_seen, grace_threshold)
        offline_slaves.append(slave_name)
        slave_wait_delta = (self._grace_period - (now - last_seen))
        if (wait_delta is None) or (slave_wait_delta > wait_delta):
          wait_delta = slave_wait_delta

      # We've looped through our stratum and found no proposed candidates. Are
      # there any preferred ones?
      if busy_slaves or offline_slaves:
        log.msg("Returning 'None' in anticipation of unavailable slaves. "
                "Please disregard the following BuildBot 'nextSlave' "
                "error: %s" % (busy_slaves + offline_slaves,))

        # We're going to return 'None' to wait for a preferred slave. If all of
        # the slaves that we're anticipating are offline, schedule a 'poke'
        # after the last candidate has exceeded its grace period to allow the
        # build to go to lower strata.
        if (not busy_slaves) and (wait_delta is not None):
          self._debug("Scheduling 'ping' for %r in %s",
                      builder.name, wait_delta)
          self._schedule_builder_timer(
              builder,
              wait_delta,
          )
        return None

    self._debug("No slaves are available; returning 'None'")
    return None

  def _debug(self, fmt, *args):
    if not self.verbose:
      return
    log.msg(fmt % args)

  @staticmethod
  def _get_all_slave_status(builder):
    # Try using the builder's BuilderStatus object to get a list of all slaves
    if builder.builder_status is not None:
      return builder.builder_status.getSlaves()

    # Satisfy with the list of currently-connected slaves
    return [slave_builder.slave.slave_status
            for slave_builder in builder.slaves]

  def _get_latest_seen_time(self, slave_status):
    times = []

    # Add all of the registered connect times
    times += [datetime.fromtimestamp(connect_time)
              for connect_time in slave_status.connect_times]

    # Add the time of the slave's last message
    times.append(datetime.fromtimestamp(slave_status.lastMessageReceived()))

    # Add the last time we've seen the slave in our 'nextSlave' function
    last_seen_time = self._slave_seen_times.get(slave_status.name)
    if last_seen_time is not None:
      times.append(last_seen_time)

    if not times:
      return None
    return max(times)

  def _record_strata(self, build_slave):
    stratum = build_slave.properties.getProperty(self._strata_property)
    strata_set = self._slave_strata_map.get(stratum)
    if strata_set is None:
      strata_set = set()
      self._slave_strata_map[stratum] = strata_set
    strata_set.add(build_slave.slavename)

  def _record_slave_seen_time(self, build_slave, now):
    self._slave_seen_times[build_slave.slavename] = now

  def _schedule_builder_timer(self, builder, delta):
    poke_builder_timer = self._poke_builder_timers.get(builder.name)
    if poke_builder_timer is None:
      poke_builder_timer = PokeBuilderTimer(
          builder.botmaster,
          builder.name,
      )
      self._poke_builder_timers[builder.name] = poke_builder_timer
    poke_builder_timer.reset(delta)

  def _cancel_builder_timer(self, builder):
    poke_builder_timer = self._poke_builder_timers.get(builder.name)
    if poke_builder_timer is None:
      return
    poke_builder_timer.cancel()
