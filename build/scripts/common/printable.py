# vim: set fileencoding=utf-8
# Copyright (c) 2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simplifies live debugging, like buildbot's manhole.

Similar to pprint except that:
- It is really to print objects and the code is 100% recursive.
- Prefers str() over repr() since it's only for debugging.
- Indent is not configurable by design and locked to 2.

Usage:
  class MyClass(Printable):
    (...)

  from printable import AutoString as A
  print A(master)
"""

# Hack to quickly display 'set'.
CONTROL_CHARS = {tuple: '()', list: '[]', set: '«»'}
SIMPLE_TYPES = (basestring, bool, buffer, xrange, int, float, long, complex,
                None.__class__)

def StrippedStr(obj, maxlen=80):
  """Strings too long are useless anyway."""
  if isinstance(obj, str):
    # Quote strings.
    b = "'%s'" % obj
  else:
    b = str(obj)
  if len(b) > maxlen:
    b = b[0:maxlen] + '...'
  return b


def AutoString(obj, depth=3, maxlen=80):
  """Returns a textual representation the members of an object for debugging.

  List member variables but not functions.
  """
  out = []
  if isinstance(obj, SIMPLE_TYPES):
    return StrippedStr(obj, maxlen)
  elif isinstance(obj, (tuple, list, set)):
    # Print each item.
    chars = CONTROL_CHARS[obj.__class__]
    if not len(obj):
      return chars
    out.append(chars[0])
    for v in obj:
      if depth > 0:
        out.extend(['  %s' % l
                    for l in AutoString(v, depth-1, maxlen).split('\n')])
        out[-1] = '%s,' % out[-1]
      else:
        out.append('  %s,' % StrippedStr(v, maxlen))
    out.append(chars[1])
    if len(out) == 3:
      out = ['%s%s%s' % (out[0], out[1].lstrip(' '), out[2])]
  elif isinstance(obj, dict):
    if not len(obj):
      return '{}'
    out.append('{')
    for (k, v) in obj.iteritems():
      if depth > 0:
        k_lines = AutoString(k, depth-1, maxlen).split('\n')
        v_lines = AutoString(v, depth-1, maxlen).split('\n')
        out.extend(['  %s' % k for k in k_lines])
        out[-1] = '%s:' % out[-1]
        if len(v_lines) > 1:
          out.extend(['    %s' % l for l in v_lines])
          out[-1] = '%s,' % out[-1]
        else:
          out[-1] = '%s %s,' % (out[-1], v_lines[0])
      else:
        out.append('  %s: %s,' % (
            StrippedStr(k, maxlen), StrippedStr(v, maxlen)))
    out.append('}')
    if len(out) == 3:
      out = ['%s%s%s' % (out[0], out[1].lstrip(' '), out[2])]
  else:
    # Standard object. Skips over __.* and callable members.
    out.append('<%s>:' % obj.__class__)
    for member_name in dir(obj):
      member_obj = getattr(obj, member_name)
      if not callable(member_obj) and not member_name.startswith('__'):
        if depth > 0:
          out.append('  %s:' % member_name)
          v_lines = AutoString(member_obj, depth-1, maxlen).split('\n')
          if len(v_lines) > 1:
            out.extend(['    %s' % l for l in v_lines])
          else:
            out[-1] = '%s %s' % (out[-1], v_lines[0])
        else:
          out.append('  %s: %s' % (
              member_name, StrippedStr(member_obj, maxlen)))
  return '\n'.join(out)


class Printable(object):
  def __str__(self):
    return AutoString(self)
