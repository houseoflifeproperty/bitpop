# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import with_statement

import codecs
import mimetypes
import socket
import urllib2

from slave.gtest.networktransaction import NetworkTransaction


def GetMimeType(filename):
  return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def _EncodeMultipartFormData(fields, files):
  """Encode form fields for multipart/form-data.

  Args:
    fields: A sequence of (name, value) elements for regular form fields.
    files: A sequence of (name, filename, value) elements for data to be
       uploaded as files.
  Returns:
    (content_type, body) ready for httplib.HTTP instance.

  Source:
    http://code.google.com/p/rietveld/source/browse/trunk/upload.py
  """
  BOUNDARY = '-M-A-G-I-C---B-O-U-N-D-A-R-Y-'
  CRLF = '\r\n'
  lines = []

  for key, value in fields:
    lines.append('--' + BOUNDARY)
    lines.append('Content-Disposition: form-data; name="%s"' % key)
    lines.append('')
    if isinstance(value, unicode):
      value = value.encode('utf-8')
    lines.append(value)

  for key, filename, value in files:
    lines.append('--' + BOUNDARY)
    lines.append('Content-Disposition: form-data; name="%s"; filename="%s"' %
                 (key, filename))
    lines.append('Content-Type: %s' % GetMimeType(filename))
    lines.append('')
    if isinstance(value, unicode):
      value = value.encode('utf-8')
    lines.append(value)

  lines.append('--' + BOUNDARY + '--')
  lines.append('')
  body = CRLF.join(lines)
  content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
  return content_type, body


class TestResultsUploader:
  def __init__(self, host):
    self._host = host

  def _upload_files(self, attrs, file_objs):
    url = "http://%s/testfile/upload" % self._host
    content_type, data = _EncodeMultipartFormData(attrs, file_objs)
    headers = {"Content-Type": content_type}
    request = urllib2.Request(url, data, headers)
    urllib2.urlopen(request)

  def upload(self, params, files, timeout_seconds):
    file_objs = []
    for filename, path in files:
      with codecs.open(path, "rb") as f:
        file_objs.append(('file', filename, f.read()))

    orig_timeout = socket.getdefaulttimeout()
    try:
      socket.setdefaulttimeout(timeout_seconds)
      NetworkTransaction(timeout_seconds=timeout_seconds).run(
        lambda: self._upload_files(params, file_objs))
    finally:
      socket.setdefaulttimeout(orig_timeout)
