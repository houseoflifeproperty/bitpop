# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Out of band HTTP push."""

import Queue
import json
import logging
import os
import threading
import time
import urllib

from verification import base


class AsyncPushNoop(object):
  url = 'http://localhost'
  def close(self):
    pass

  def send(self, pending, packet):
    pass

  @staticmethod
  def _package(pending, packet):
    data = {
      'done': pending.get_state() not in (base.PROCESSING, base.IGNORED),
      'issue': pending.issue,
      'owner': pending.owner,
      'patchset': pending.patchset,
      'timestamp': time.time(),
    }
    if packet:
      data.update(packet)
    return data


class AsyncPushStore(AsyncPushNoop):
  """Saves all the events into workdir/events.json for later analysis."""
  def __init__(self):
    super(AsyncPushStore, self).__init__()
    self.queue = []

  def close(self):
    with open(os.path.join('workdir', 'events.json'), 'w') as f:
      json.dump(self.queue, f, indent=2)

  def send(self, pending, packet):
    self.queue.append(self._package(pending, packet))


class AsyncPush(AsyncPushNoop):
  """Sends HTTP Post in a background worker thread."""
  _TERMINATE = object()

  def __init__(self, url, password):
    super(AsyncPush, self).__init__()
    assert url
    assert password
    self.url = url
    self.password = password
    self.queue = Queue.Queue()
    self.thread = threading.Thread(target=self._worker_thread)
    self.thread.daemon = True
    self.thread.start()

  def close(self):
    self.queue.put(self._TERMINATE)
    self.thread.join()

  def send(self, pending, packet):
    """Queues a packet."""
    self.queue.put(self._package(pending, packet))

  def _get_items(self):
    """Waits for an item to be queued and returns up to 10 next items if queued
    fast enough.
    """
    items = [self.queue.get()]
    try:
      for _ in range(9):
        items.append(self.queue.get_nowait())
    except Queue.Empty:
      pass
    return items

  def _worker_thread(self):
    """Sends the packets in a loop through HTTP POST."""
    params = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Accept': 'text/plain'
    }
    done = False
    while not done:
      items = self._get_items()
      if self._TERMINATE in items:
        done = True
        logging.debug('Worker thread exiting')
        items.remove(self._TERMINATE)
      url = self.url + '/receiver'
      logging.debug('Sending %d items to %s' % (len(items), url))
      try:
        data = [('p', json.dumps(item)) for item in items]
        data.append(('password', self.password))
        urllib.urlopen(url, urllib.urlencode(data), params).read()
      except IOError, e:
        logging.error(e)
        for item in items:
          self.queue.put(item)
        if not done:
          time.sleep(1)
        # Don't retry if done.
