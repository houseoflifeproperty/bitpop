# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Generically-useful IBodyProducer implementations"""

import json

from twisted.internet import defer
from twisted.web import iweb
from zope.interface import implements

# Disable missing '__init__' method | pylint: disable=W0232
class IMIMEBodyProducer(iweb.IBodyProducer):
  """Interface that extends an 'IBodyProducer' allow it to supply a MIME type.
  """

  def getMIMEType(self):
    """
    Returns the MIME type for this body producer
    Returns: (str) The MIME type
    """


class StringBodyProducer(object):
  """An IBodyProducer implementation that directly produces a string."""
  implements(IMIMEBodyProducer)

  def __init__(self, body_str, mime_type=None):
    self.body_str = body_str
    self.length = len(self.body_str)

    self.mime_type = mime_type
    if self.mime_type is None:
      self.mime_type = 'text/plain'

  # IMIMEBodyProducer
  def getMIMEType(self):
    return self.mime_type

  def startProducing(self, consumer):
    consumer.write(self.body_str)
    self.body_str = ''
    self.length = 0
    return defer.succeed(None)

  def stopProducing(self):
    pass

  def pauseProducing(self):
    pass

  def resumeProducing(self):
    pass


class JsonBodyProducer(StringBodyProducer):
  """An IBodyProducer implementation that produces the JSON associated with a
  Python dictionary."""

  def __init__(self, json_dict):
    StringBodyProducer.__init__(
        self,
        json.dumps(json_dict),
        mime_type='application/json')

