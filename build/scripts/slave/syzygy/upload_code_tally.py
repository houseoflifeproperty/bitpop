#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to upload a converted code tally json file to the dashboard."""

import httplib
import math
import optparse
import random
import sys
import time
import urllib
import urllib2

UPLOAD_PATH = '/upload_sizes'


def UploadCodeTallyJson(server, json_file):
  """Reads in the json_file and sends it to the given server."""
  with open(json_file, 'r') as f:
    json_data = f.read()

  data = urllib.urlencode({'data': json_data})
  req = urllib2.Request(server + UPLOAD_PATH, data)

  # If the upload encounters an exception that doesn't seem to be this scripts
  # fault, retry a few times.
  for attempt in range(5):
    try:
      urllib2.urlopen(req)
      print 'Sucessfully uploaded data to server'
      return 0
    except urllib2.HTTPError as e:
      if e.code < 500:
        print 'Encounter an exception, not retrying.\n%s' % str(e)
        return 1
      print 'Encountered a server error, retrying\n%s' % str(e)
    except (httplib.HTTPException, urllib2.URLError) as e:
      print 'Encountered an exception, retrying.\n%s' % str(e)

    # Add an exponential backoff.
    duration = random.random() * 3 + math.pow(1.5, (attempt + 1))
    duration = min(10, max(0.1, duration))
    time.sleep(duration)

  print 'Unable to upload to the server after 5 attempts, aborting.'
  return 1


def main():
  parser = optparse.OptionParser('USAGE: %prog <server> <code tally json>')
  (_, args) = parser.parse_args()

  if len(args) !=2:
    parser.error('Must specify <server> and <code tall json> as args')

  return UploadCodeTallyJson(args[0], args[1])

if __name__ == '__main__':
  sys.exit(main())
