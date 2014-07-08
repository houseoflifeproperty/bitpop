# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
from cStringIO import StringIO
import json
import netrc
import urlparse

from twisted.internet import defer, protocol, reactor
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web import iweb

from zope.interface import implements

# pylint: disable=W0105
"""
Class for sending http requests to a gerrit server, and parsing the
json-formatted responses.
"""


DEBUG = False
NETRC = netrc.netrc()


class GerritError(RuntimeError):
  def __init__(self, msg, http_code):
    super(GerritError, self).__init__(msg)
    self.http_code = http_code

  def __str__(self):
    s = super(GerritError, self).__str__()
    return '[http_code=%d] %s' % (self.http_code, s)


class JsonResponse(protocol.Protocol):
  """Receiver protocol to parse a json response from gerrit."""

  @staticmethod
  def Get(response, url=None):
    """
    Given a Response object returned by GerritAgent.request, parse the json
    body of the response.
    """
    finished = defer.Deferred()
    response.deliverBody(JsonResponse(url, finished))
    return finished

  def __init__(self, url, finished):
    self.url = url
    self.finished = finished
    self.buf = StringIO()
    self.reply = None

  def dataReceived(self, _bytes):
    self.buf.write(_bytes)

  # pylint: disable=W0222
  def connectionLost(self, _):
    body = self.buf.getvalue()
    if not body:
      self.finished.callback(None)
      return
    errmsg = 'Mal-formed json response from %s' % self.url
    if body[0:4] != ")]}'":
      self.finished.errback(errmsg)
      return
    try:
      self.reply = json.loads(body[4:])
      if DEBUG:
        log.msg(json.dumps(self.reply, indent=2))
      self.finished.callback(self.reply)
    except ValueError:
      self.finished.errback(errmsg)


class JsonBodyProducer:

  implements(iweb.IBodyProducer)

  def __init__(self, text):
    self.text = text
    self.length = len(text)

  def startProducing(self, consumer):
    consumer.write(self.text)
    self.text = ''
    self.length = 0
    return defer.succeed(None)

  def stopProducing(self):
    pass


class GerritAgent(Agent):

  gerrit_protocol = 'https'

  def __init__(self, gerrit_host, *args, **kwargs):
    url_parts = urlparse.urlparse(gerrit_host)
    if url_parts.scheme:
      self.gerrit_protocol = url_parts.scheme
    self.gerrit_host = url_parts.netloc

    auth_entry = NETRC.authenticators(self.gerrit_host.partition(':')[0])
    if auth_entry:
      self.auth_token = 'Basic %s' % (
          base64.b64encode('%s:%s' % (auth_entry[0], auth_entry[2])))
    else:
      self.auth_token = None
    Agent.__init__(self, reactor, *args, **kwargs)

  # pylint: disable=W0221
  def request(self, method, path, headers=None, body=None, expected_code=200,
              retry=0, delay=0):
    """
    Send an http request to the gerrit service for the given path.

    If 'retry' is specified, transient errors (http response code 500-599) will
    be retried after an exponentially-increasing delay.

    Returns a Deferred which will call back with the parsed json body of the
    gerrit server's response.

    Args:
      method: 'GET', 'POST', etc.
      path: Path element of the url.
      headers: dict of http request headers.
      body: json-encodable body of http request.
      expected_code: http response code expected in reply.
      retry: How many times to retry transient errors.
      delay: Wait this many seconds before sending the request.
    """
    retry_delay = delay * 2 if delay else 0.5
    retry_args = (
        method, path, headers, body, expected_code, retry - 1, retry_delay)
    if not path.startswith('/'):
      path = '/' + path
    if not headers:
      headers = Headers()
    else:
      # Make a copy so mutations don't affect retry attempts.
      headers = Headers(dict(headers.getAllRawHeaders()))
    if self.auth_token:
      if not path.startswith('/a/'):
        path = '/a' + path
      headers.setRawHeaders('Authorization', [self.auth_token])
    url = '%s://%s%s' % (self.gerrit_protocol, self.gerrit_host, path)
    if body:
      body = JsonBodyProducer(json.dumps(body))
      headers.setRawHeaders('Content-Type', ['application/json'])
    if DEBUG:
      log.msg(url)
    if delay:
      d = defer.succeed(None)
      d.addCallback(
          reactor.callLater, delay, Agent.request, self, method, str(url),
          headers, body)
    else:
      d = Agent.request(self, method, str(url), headers, body)
    def _check_code(response):
      if response.code == expected_code:
        return response
      if retry > 0 and response.code >= 500 and response.code < 600:
        return self.request(*retry_args)
      msg = 'Failed gerrit request (code %s, expected %s): %s' % (
          response.code, expected_code, url)
      raise GerritError(msg, response.code)
    d.addCallback(_check_code)
    d.addCallback(JsonResponse.Get, url=url)
    return d
