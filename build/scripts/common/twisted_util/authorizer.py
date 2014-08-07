# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""IAuthorizer class implementations"""

import base64
import netrc
import urlparse

from zope.interface import implements, Interface

# Disable missing '__init__' method | pylint: disable=W0232
class IAuthorizer(Interface):
  """Interface to augment an HTTP request with implementation-specific
  authorization data.
  """

  def addAuthHeadersForURL(self, headers, url):
    """
    Augments a set of HTTP headers with this authorizer's authorization data
    for the requested URL. If no authorization is needed for the URL, no
    headers will be added.

    Arguments:
      headers: (Headers) the headers to augment
      url: (str) the URL to authorize

    Returns: (bool) True if authorization was added, False if not.
    """


class NETRCAuthorizer(object):
  """An Authorizer implementation that loads its authorization from a '.netrc'
  file.
  """
  implements(IAuthorizer)

  def __init__(self, netrc_path=None):
    """Initializes a new NetRC Authorizer

    Args:
      netrc_path: (str) If not None, use this as the 'netrc' file path;
          otherwise, use '~/.netrc'.
    """
    self._netrc = netrc.netrc(netrc_path)

  def addAuthHeadersForURL(self, headers, url):
    parsed_url = urlparse.urlparse(url)
    auth_entry = self._netrc.authenticators(parsed_url.hostname)
    if auth_entry is not None:
      auth_token = 'Basic %s' % \
        base64.b64encode('%s:%s' % (auth_entry[0], auth_entry[2]))
      headers.setRawHeaders('Authorization', [auth_token])
      return True
    return False
