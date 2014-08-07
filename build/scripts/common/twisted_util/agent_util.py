# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility and helper functions for 'twisted' library use and integration."""

import urlparse

from twisted.web.http_headers import Headers

__all__ = [
    'CloneHeaders',
    'ToRelativeURL',
    'RelativeURLJoin',
]


def CloneHeaders(headers):
  """Clones (or creates) a HTTP Headers object.

  Args:
    headers: (Headers or None) If None, a new empty Headers object is created;
        otherwise, the Headers object to clone.
  Returns: (Headers) An independent clone of the initial Headers object.
  """
  if headers is None:
    return Headers()
  return Headers(dict(headers.getAllRawHeaders()))

def ToRelativeURL(path):
  """Converts a URL path into a relative URL path.

  This function transforms a URL into a relative URL by stripping initial
  separators.

  Args:
    path: (str) The base URL
  Returns: (str) The relative URL
  """
  while path.startswith('/'):
    path = path[1:]
  return path

def RelativeURLJoin(base, path):
  """Constructs a URL by concatenating a relative path to a base URL.

  This function is more forgiving than 'urlparse.urljoin' in that it will
  automatically format 'base' and 'path' such that they become absolute and
  relative URLs respectively.

  Args:
    base: (str) The base URL
    path: (str) The relative URL path to join
  Returns: (str) The constructed URL
  """
  if not base.endswith('/'):
    base = base + '/'
  return urlparse.urljoin(
      base,
      ToRelativeURL(path)
  )
