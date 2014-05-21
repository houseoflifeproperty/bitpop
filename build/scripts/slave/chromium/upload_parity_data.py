#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import glob
import httplib
import os
import socket
import stat
import subprocess
import sys
import urllib
import urlparse

def find_test_names(path):
  print "Looking for tests in %s" % path
  p1 = subprocess.Popen([path, "--gtest_list_tests"],
                        stdout=subprocess.PIPE)
  lines = p1.communicate()[0].splitlines()
  prefix = ''
  tests = []
  for test in lines:
    test = test.strip()
    if len(test) <= 0:
      continue

    if test.find('YOU HAVE') > 0:
      continue

    if test.rfind('.') > 0:
      prefix = test
      continue

    tests.append(prefix + test)

  return tests

def get_tests(path):
  tests = glob.glob(os.path.join(path, "*_*tests*"))
  return [x for x in tests
          if os.stat(x)[stat.ST_MODE] & stat.S_IXUSR
          and not stat.S_ISDIR(os.stat(x)[stat.ST_MODE])]

def all_tests(path):
  skip_tests = set(['omx_unittests',
                    'ffmpeg_tests',
                    'chrome_frame_tests',
                    'chrome_frame_net_tests',
                    'chrome_frame_perftests',
                    'chrome_frame_reliability_tests',
                    'chrome_frame_unittests'])
  tests = get_tests(path)
  tests_for_binary = {}
  for test in tests:
    name = os.path.splitext(os.path.basename(test))[1]
    if name in skip_tests:
      continue
    tests_for_binary[name] = find_test_names(test)

  return tests_for_binary

class Error(Exception):
  """Base-class for exceptions in this module."""


class PostError(Error):
  """An error has occured while trying to post data to the server."""


class BadServerStatusError(PostError):
  """The server has returned an error while importing data."""

def split_url(url):
  """Splits an HTTP URL into pieces.

  Args:
    url: String containing a full URL string (e.g.,
      'http://blah.com:8080/stuff?param=1#foo')

  Returns:
    Tuple (netloc, uri) where:
      netloc: String containing the host/port combination from the URL. The
        port is optional. (e.g., 'blah.com:8080').
      uri: String containing the relative URI of the URL. (e.g., '/stuff').
  """
  _, netloc, path, _, _ = urlparse.urlsplit(url)
  return netloc, path

def upload_data(tests_for_binary, url, platform):
  host_port, uri = split_url(url)
  print "Posting data to %s" % host_port

  for (binary, tests) in tests_for_binary.items():
    print "Updating data for %s." % binary
    try:
      body = urllib.urlencode({
          'binary': binary,
          'platform': platform,
          'tests': '\n'.join(tests),
          })

      headers = {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Content-Length': len(body),
          }

      connection = httplib.HTTPConnection(host_port)
      try:
        connection.request('POST', uri, body, headers)
        response = connection.getresponse()

        status = response.status
        reason = response.reason
        response.read()
        if status != httplib.OK:
          raise BadServerStatusError('Received code %d: %s, %s %d tests\n' % (
              status, reason, binary, len(tests)))
      finally:
        connection.close()

    except (IOError, httplib.HTTPException, socket.error), e:
      raise PostError(e)
  return 0


def main():
  path = sys.argv[1]
  url = sys.argv[2]
  platform = sys.argv[3]

  tests = all_tests(path)
  for binary in tests:
    for test in tests[binary]:
      print "%s:%s" % (binary, test)

  return upload_data(tests, url, platform)


if __name__ == "__main__":
  sys.exit(main())
