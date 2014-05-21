# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from twisted.application import strports
from twisted.internet import defer
from twisted.python import log
from twisted.web import http

from master.try_job_base import TryJobBase


class TryJobHTTPRequest(http.Request):
  def __init__(self, channel, queued):
    http.Request.__init__(self, channel, queued)

  def process(self):
    try:
      # Support only one URI for now.
      if self.uri != '/send_try_patch':
        log.msg("Received invalid URI: %s" % self.uri)
        self.code = http.NOT_FOUND
        return

      options = dict((k, v) for k, v in self.args.iteritems() if v)
      self.channel.factory.parent.messageReceived(options)
      self.code = 200
    finally:
      self.code_message = http.RESPONSES[self.code]
      self.write(self.code_message)
      self.finish()


class TryJobHTTP(TryJobBase):
  """Opens a HTTP port to accept patch files and to execute these on the try
  server."""

  def __init__(self, name, pools, port, userpass=None, properties=None,
               last_good_urls=None, code_review_sites=None):
    TryJobBase.__init__(self, name, pools, properties,
                        last_good_urls, code_review_sites)
    if type(port) is int:
      port = "tcp:%d" % port
    self.port = port
    f = http.HTTPFactory()
    f.protocol.requestFactory = TryJobHTTPRequest
    f.parent = self
    s = strports.service(port, f)
    s.setServiceParent(self)
    log.msg('TryJobHTTP listening on port %s' % self.port)

  def getPort(self):
    """Utility method for tests: figure out which TCP port we just opened."""
    # Access to a protected member
    # pylint: disable=W0212
    # TODO(maruel): BROKEN ON BULDBOT 0.8.4p1
    # pylint: disable=E1101
    return self.services[0]._port.getHost().port

  @defer.deferredGenerator
  def messageReceived(self, options):
    parsed = self.parse_options(options)
    wfd = defer.waitForDeferred(self.get_lkgr(parsed))
    yield wfd
    wfd.getResult()

    wfd = defer.waitForDeferred(self.master.addChange(
      author=','.join(parsed['email']),
      revision=parsed['revision'],
      comments=''))
    yield wfd
    changeids = [wfd.getResult().number]

    self.SubmitJob(parsed, changeids)
