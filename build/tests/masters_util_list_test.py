#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import masters_util


def flatten(lol):
  """Returns a list of the contents of a list of lists."""

  result = []
  for sub in lol:
    result.extend(sub)
  return result


def test_assertions(subject, degree):
  subs = masters_util.sublists(subject, degree)
  assert flatten(subs) == subject
  for x in subs:
    assert len(x) <= degree


def test_slice(subject):
  for degree in range(1, len(subject)+2):
    test_assertions(subject, degree)


def run_test():
  test_slice(range(10))
  test_slice(range(100))
  test_slice(range(1000))
  test_slice(range(3))
  test_slice(range(2))
  test_slice(range(1))
  test_slice(['foo'])
  test_slice([])
  return True


run_test()
