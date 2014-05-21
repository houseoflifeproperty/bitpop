# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import itertools
import time

class FailuresHistory(object):
  """ Stores the history of recent build failures.
      The failures are identified by their unique ID
      (e.g. failed test, memory suppression hash, etc)

      This class is similar to LRU but it also stores counts.
      We don't need very precise data for "old" builds.
  """

  def __init__(self, expiration_time, size_limit):
    """ expiration_time: don't count failures older than that (in seconds)
        size_limit: drop some old builds when we reach this size.
                    It's not a hard limit but rather a recommendation.
    """
    self.expiration_time = expiration_time
    assert size_limit > 1
    self.size_limit = size_limit
    self.full_cleanup_delay = 0

    self.failures = {}  # Key: failure_id, Value: list of failure times.
    self.failures_count = 0

  def Put(self, failure_id):
    self.failures.setdefault(failure_id, []).append(time.time())
    self.failures_count += 1
    self._Cleanup(failure_id)
    self._MaybeCleanupFull()

  def GetCount(self, failure_id):
    if failure_id in self.failures:
      self._Cleanup(failure_id)

    return len(self.failures.get(failure_id, []))

  def _MaybeCleanupFull(self):
    """ Checks the size vs size_limit and maybe aggressively
        cleanup all the queues. The slow path is executed at most once of
        self.size_limit invocations to avoid O(N^2) perf problems.
    """
    if self.failures_count <= self.size_limit:
      return  # no cleanup needed yet.

    # We delay full cleanups to avoid doing them on each Put() when we have many
    # singular failures. Otherwise, we'd end up with a O(N^2) algorithm.
    if self.full_cleanup_delay > 0:
      self.full_cleanup_delay -= 1
      return
    self.full_cleanup_delay = self.size_limit

    # If we're lucky, dropping the expired failures is enough.
    for f_id in self.failures.keys():
      self._Cleanup(f_id)
    if self.failures_count <= self.size_limit:
      return

    # Slow path - flatten the dictionary of failures, sort by timestamp,
    # trim the oldest ones. The complexity is O(N*log N) where N is the number
    # of failures recorded.
    all_items = itertools.chain.from_iterable(
        ((f_id, t) for t in timestamps)
            for f_id, timestamps in self.failures.iteritems())
    all_items = sorted(all_items, key=lambda x: x[1])
    drop_items_counts = defaultdict(int)
    for f_id, _ in all_items[:-self.size_limit]:
      # There's a tiny chance we'll count the 'recent' failure to remove
      # but we don't bother.
      drop_items_counts[f_id] += 1

    for f_id, drop_count in drop_items_counts.iteritems():
      self.failures[f_id] = self.failures[f_id][drop_count:]
      self.failures_count -= drop_count
      if not self.failures[f_id]:
        del self.failures[f_id]

    assert self.failures_count <= self.size_limit

  def _Cleanup(self, failure_id):
    """ Drops old builds for a given failure ID. """
    drop_older_than = time.time() - self.expiration_time
    assert failure_id in self.failures
    if self.failures[failure_id][0] >= drop_older_than:
      return

    old = self.failures[failure_id]
    # Make sure the list of failure times is sorted.
    assert all(old[i] <= old[i+1] for i in xrange(len(old) - 1))
    self.failures[failure_id] = [x for x in old if x > drop_older_than]
    self.failures_count += len(self.failures[failure_id]) - len(old)
    if not self.failures[failure_id]:
      del self.failures[failure_id]
