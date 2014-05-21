#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Replay server for Gmail benchmark."""


import BaseHTTPServer
import binascii
import cgi
from hashlib import md5 # pylint: disable=E0611
from optparse import OptionParser
import os
import re
import simplejson as json
import SocketServer
import sys
import urllib

_BUSTERS = ['random', 'zx', 'ai', 'ik', 'jsid', 'it', 'seid', 'rid']

_UPHEADERS = ['Refresh', 'Content-Type', 'Set-Cookie']

_LOCATION = ('/berlin.zrh.corp.google.com:9380/mail/'
            '?shva=1&jsmode=DEBUG_OPTIMIZED#')

def DefReBuster(buster):
  return buster + r'((' + urllib.quote_plus('=') + r')|=)[^\&]+'

_RE_BUSTERS = [re.compile(DefReBuster(buster_)) for buster_ in _BUSTERS]


def __RemoveCacheBusters(path):
  for re_buster in _RE_BUSTERS:
    path = re.sub(re_buster, '', path)
  return path


class ProxyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """Proxy handler class."""

  def __init__(self, request, client_address, server, benchmark):
    self.benchmark = benchmark
    BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request,
                                                   client_address, server)

  def do_GET(self):
    """The GET handler."""
    if self.path == '/':
      self.send_response(302)
      self.send_header('Location', _LOCATION)
      self.end_headers()
      return
    else:
      self.__ProcessRequest()

  def do_POST(self):
    """The post handler.

    Handles replayed post requests as well as result reporting
    """
    if self.path.startswith('/postResult'):
      self.__PostResults()
    else:
      self.do_GET()

  do_HEAD = do_GET
  do_PUT = do_GET
  do_CONNECT = do_GET

  def __BrowserString(self):
    agent = str(self.headers['user-agent'])
    substrings = []
    position = 0
    depth = 0
    for i in xrange(len(agent)):
      if agent[i] == '(':
        if depth == 0:
          substrings.append(agent[position:i])
        depth += 1
      if agent[i] == ')':
        depth -= 1
        if depth == 0:
          position = i + 1
    substrings.append(agent[position:])
    agent = ''.join(substrings)
    agent = re.sub('\([^\)]+\)', '', agent)
    agent = re.sub('\/[0-9.]+', '', agent)
    agent = re.sub(' +', '-', agent)
    return agent.lower()

  def __ProcessRequest(self):
    browserstring = self.__BrowserString()
    path = __RemoveCacheBusters(self.path)[1:]
    key = md5(path).hexdigest()
    try:
      cachedresponse = self.benchmark.GetResponse(browserstring, key)
    except KeyError:
      self.send_response(404, 'Not in cache!')
      return

    self.send_response(int(cachedresponse['code']), 'I have my reasons.')
    for key, value in cachedresponse['header'].iteritems():
      if key in _UPHEADERS:
        self.send_header(key, value)
    self.end_headers()
    self.wfile.write(cachedresponse['body'])

  def __PostResults(self):
    length = int(self.headers['content-length'])
    result = cgi.parse_qs(self.rfile.read(length))['result'][0]
    result = json.loads(result)[0]
    self.benchmark.PostResult(result)
    self.send_response(200, 'Got it.')
    # Needed for goog.net.IframeIo, which checks the body to
    # see if the request worked.
    self.wfile.write('<html><body>OK</body></html>')

  def log_request(self, code='-', size='-'):
    pass


class ThreadingHTTPServer(SocketServer.ThreadingMixIn,
                          BaseHTTPServer.HTTPServer):
  pass


class ReplayBenchmark(object):
  """Main benchmark class."""

  def __init__(self, callback, data_dir, port):

    self.__callback = callback
    self.__responses = {}
    self.__port = port
    self.__httpd = ThreadingHTTPServer(
        ('', self.__port),
        ReplayBenchmark.__HandleRequest.__get__(self))
    self.__LoadCachedResponses(data_dir)

  def RunForever(self):
    print 'Listening on port %d.' % self.__port
    self.__httpd.serve_forever()

  def PostResult(self, json_string):
    self.__callback(json_string)

  def GetResponse(self, browserstring, key):
    return self.__responses[browserstring][key]

  def __HandleRequest(self, request, client_address, server):
    return ProxyHandler(request, client_address, server, self)

  def __LoadCachedResponses(self, base_dir):
    """Preload all cached responses."""
    print 'Loading data...'
    for browser in os.listdir(base_dir):
      filesread = 0
      if not os.path.isdir(os.path.join(base_dir, browser)):
        continue
      self.__responses[browser] = {}
      print 'Reading responses for', browser,
      for key in os.listdir(os.path.join(base_dir, browser)):
        sys.stdout.flush()
        f = open(os.path.join(base_dir, browser, key))
        cachedresponse = json.load(f)
        f.close()
        if filesread % 10 == 0:
          print '.',
        repl = ''
        if cachedresponse['body']:
          lines = cachedresponse['body'].split('\n')
        else:
          lines = []

        for line in lines:
          repl += binascii.a2b_uu(line)
          # signal that we are in replay mode.

          # uudecode here, or uuencode in php inserts a lot of 0 chars.
          # will be fixed when we get rid of php.

        repl = repl.replace(chr(0), '')
        repl = re.sub('<script>', '<script>DEV_BENCHMARK_REPLAY=1;', repl)
        self.__responses[browser][key] = {
            'code': cachedresponse['code'],
            'header': cachedresponse['header'],
            'body': repl
            }
        filesread += 1
      print filesread, 'read.'


def PrintResult(result):
  print json.dumps(result)


def main():
  parser = OptionParser()
  parser.add_option('-p', '--port', dest='port', type='int', default=8000)
  parser.add_option('-d', '--dir', dest='dir', type='string')
  options = parser.parse_args()[0]
  benchmark = ReplayBenchmark(PrintResult, options.dir, options.port)
  benchmark.RunForever()

if __name__ == '__main__':
  main()
