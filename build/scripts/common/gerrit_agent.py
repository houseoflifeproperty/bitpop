# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Twisted implementation of an interface to the Gerrit REST API and
associated JSON objects."""

import json
import urlparse

from common.twisted_util.agent import Agent
from common.twisted_util.agent_util import ToRelativeURL, RelativeURLJoin
from common.twisted_util.response import JsonResponse
from common.twisted_util.body_producers import JsonBodyProducer
from common.twisted_util.authorizer import NETRCAuthorizer
from twisted.python import log


class GerritJsonResponse(JsonResponse):
  """JsonResponse specialization for Gerrit responses.

  Gerrit includes a header in its JSON responses to prevent XSS attacks:
  https://gerrit-review.googlesource.com/Documentation/rest-api.html#output

  This class strips that off before allowing standard JSON processing to
  happen on the remainder of the body.
  """

  GERRIT_JSON_HEADER = ")]}'"

  def _processBody(self, body):
    if not body.startswith(self.GERRIT_JSON_HEADER):
      raise ValueError("Mal-formed JSON response does not begin with Gerrit "
                       "JSON header: (%r != %r)" % (
                           body[:len(self.GERRIT_JSON_HEADER)],
                           self.GERRIT_JSON_HEADER))
    return JsonResponse._processBody(
        self,
        body[len(self.GERRIT_JSON_HEADER):]
    )


class GerritAgent(Agent):
  """An 'Agent' that is specialized to query Gerrit servers.
  """

  def __init__(self, host, *args, **kwargs):
    # Use 'HTTPS' as the default protocol (backwards compatibility)
    url = urlparse.urlparse(host)
    if url.scheme == '':
      host = 'https://%s' % (host,)
      is_https = True
    elif url.scheme == 'https':
      is_https = True
    else:
      is_https = False

    # Use 'NETRCAuthorizer' if none is provided (backwards-compatibility), but
    # only for HTTPS.
    if (kwargs.get('authorizer') is None) and (is_https):
      log.msg("Using default 'NETRC' authorizer for HTTPS connection")
      kwargs['authorizer'] = NETRCAuthorizer()
    super(GerritAgent, self).__init__(host, *args, **kwargs)

  # Overrides 'Agent._buildRequest'
  def _buildRequest(self, path, headers):
    """Constructs a Gerrit request.

    See 'Agent._buildRequest' for details.
    """
    # Add authorization
    if self._authorizer is not None:
      if self._authorizer.addAuthHeadersForURL(
          headers,
          self.base_url):
        # Switch to authenticated Gerrit URL
        path = ToRelativeURL(path)
        if not path.startswith('a/'):
          path = RelativeURLJoin('a/', path)
      elif self.verbose:
        log.msg("No authentication for URL %r" % (self.base_url,))
    return RelativeURLJoin(self.base_url, path)

  # Disable argument number difference | pylint: disable=W0221
  def request(self, method, path, body=None, protocol=None, **kwargs):
    """Makes a request to a Gerrit server.

    'protocol' is a function that accepts a 'Response' object and
    returns a Deferred whose return value is the loaded body. Some examples of
    such functions are:
      - StringResponse.Get
      - GerritJsonResponse.Get
    If omitted, the 'GerritJsonResponse.Get' function will be used, treating
    the Gerrit response as JSON and deserializing it as a return value.

    Args:
      method: (str) The HTTP request type (GET, PUT, POST, DELETE)
      path: (str) The path within the Agent's host to query
      body: (object) If not 'None', the JSON object to serialize as the HTTP
          request body.
      protocol: (func) The Response processing function; if omitted, the
          Response will be treated as JSON and deserialized.
      kwargs: Remaining keyword arguments to 'Agent.request'
    Returns: (Deferred) By default, the Deferred will return the JSON response;
        this can be overridden via the 'protocol' parameter.
    """
    if body is not None:
      kwargs.setdefault('body_producer', JsonBodyProducer(body))
    default_json = (protocol is None)
    if default_json:
      protocol = GerritJsonResponse.Get

    d = super(GerritAgent, self).request(
        method,
        path,
        **kwargs)
    d.addCallback(protocol)

    if (self.verbose) and (default_json):
      def cbDumpResponse(response):
        log.msg("Gerrit response:\n", json.dumps(response, indent=2))
        return response
      d.addCallback(cbDumpResponse)

    return d
