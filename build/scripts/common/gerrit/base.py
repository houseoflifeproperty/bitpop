# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class GerritError(Exception):
  """An Exception subtype that represents a Gerrit server error."""
  pass


# The XSS-prevention header that Gerrit prefixes its JSON responses with
GERRIT_JSON_HEADER = ")]}'"
