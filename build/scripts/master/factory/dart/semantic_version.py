# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Copyright (c) 2012, the Dart project authors.  Please see the AUTHORS file
# for details. All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.

# This is a pylint fixed and scaled down version of:
# https://github.com/dart-lang/pub-dartlang/blob/master/app/
# models/semantic_version.py

import re
from functools import total_ordering

@total_ordering
class SemanticVersion(object):
  """A semantic version number. See http://semver.org/."""

  _RE = re.compile(r"""
      ^
      (\d+)\.(\d+)\.(\d+)                  # Version number.
      (?:-([0-9a-z-]+(?:\.[0-9a-z-]+)*))?  # Pre-release.
      (?:\+([0-9a-z-]+(?:\.[0-9a-z-]+)*))? # Build.
      $                                    # Consume entire string.
      """, re.VERBOSE | re.IGNORECASE)

  def __init__(self, version):
    """Parse a semantic version string."""

    match = SemanticVersion._RE.match(version)
    if not match:
      raise ValueError('"%s" is not a valid semantic version.' % version)

    self.major = int(match.group(1))
    self.minor = int(match.group(2))
    self.patch = int(match.group(3))
    self.prerelease = _split(match.group(4))
    self.build = _split(match.group(5))
    self._text = version

  def __eq__(self, other):
    if not isinstance(other, SemanticVersion): return False
    return self._key() == other._key() # pylint: disable=W0212

  def __ne__(self, other):
    return not (self == other)

  def __lt__(self, other):
    return self._key() < other._key() # pylint: disable=W0212

  def __cmp__(self, other):
    if not isinstance(other, SemanticVersion):
      other = SemanticVersion(other)
    return cmp(self._key(), other._key()) # pylint: disable=W0212

  def _key(self):
    """The key to use for equality and ordering comparisons."""
    return (self.major, self.minor, self.patch,
            self._prerelease_key(), self._build_key())

  def _prerelease_key(self):
    """The key to use for prerelease versions.

    This is modified from the basic prerelease list to support the semantic
    version spec's ordering requirements. The first element is 1 if no
    prerelease components exists, and 0 if one does; this ensures that
    prerelease components sort below release versions.

    Each sub-component of the prerelease component is prefixed with a 0 for
    integer components and a 1 for string components, since integers sort
    below strings in semver."""

    if self.prerelease is None: return [1]
    return [0] + [(0 if isinstance(subcomponent, int) else 1, subcomponent)
                  for subcomponent in self.prerelease]

  def _build_key(self):
    """The key to use for build versions.

    This is modified from the basic build list to support the semantic
    version spec's ordering requirements. Each sub-component of the build
    component is prefixed with a 0 for integer components and a 1 for string
    components, since integers sort below strings in semver."""

    if self.build is None: return None
    return [(0 if isinstance(subcomponent, int) else 1, subcomponent)
            for subcomponent in self.build]

  def __str__(self): return self._text

  def __repr__(self):
    return 'SemanticVersion({0!r})'.format(str(self))

def _split(string):
  """Split a prerelease or build string as per the semver spec.

  Specifically, splits the string on periods, then converts every section that
  contains only numeric digits to an integer.
  """

  if string is None: return
  def maybe_make_int(substring):
    if re.search(r'[^0-9]', substring): return substring
    return int(substring)
  return map(maybe_make_int, string.split('.'))
