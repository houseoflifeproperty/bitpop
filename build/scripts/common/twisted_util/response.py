# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Implementation of Twisted Response protocols.

The twisted.web.client.Agent class reads its response iteratively from a
Protocol via its 'deliverBody' method. This module provides Protocol
implementations to read common response types.
"""

import json

from cStringIO import StringIO
from twisted.internet import defer, protocol
from twisted.python import failure


__all__ = [
    'StringResponse',
    'JsonResponse',
]


class StringResponse(protocol.Protocol):
  """Receiver protocol to receive generic string bodies."""

  @classmethod
  def Get(cls, response):
    """
    Given a Response object returned by 'Agent.request', process the body
    of the response.
    """
    finished = defer.Deferred()
    response.deliverBody(cls(finished))
    return finished

  def __init__(self, finished):
    self.finished = finished
    self.buf = StringIO()
    self.reply = None

  def dataReceived(self, data):
    self.buf.write(data)

  def connectionLost(self, reason=protocol.connectionDone):
    body = self.buf.getvalue()
    self.buf.close()

    try:
      self.reply = self._processBody(body)
    except Exception:
      self.finished.errback(failure.Failure())
      return
    self.finished.callback(self.reply)

  # Disable 'method could be a function'; we want the option of using 'self' in
  # overrides | pylint: disable=R0201
  def _processBody(self, body):
    """Processes the response body.

    Args:
      body: (str) The response body
    Returns: The response object that will be passed through 'finished'.
    """
    return body


class JsonResponse(StringResponse):
  """Receiver protocol to parse a JSON response from 'Agent.request'."""

  def _processBody(self, body):
    """Converts the HTTP body containing JSON into a deserialized JSON object.

    Args:
      body: (str) The response body value.
    """
    return json.loads(body)
