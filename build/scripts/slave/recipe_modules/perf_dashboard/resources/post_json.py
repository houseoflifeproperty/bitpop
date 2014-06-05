# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Standalone python script to post a json blob to a given url.
Internally this is to be used by the chromium_perf_post recipe module.
"""

import json
import os
import sys
import urllib

# Add requests to path
RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(
    os.path.join(RESOURCE_DIR, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'third_party', 'requests_1_2_3'))

import requests

def main():
  """See perf_dashboard/api.py, def post(...) for format of |args|."""
  args = json.load(sys.stdin)
  json.dump(args['data'], sys.stdout, indent=4, sort_keys=True)
  url = args['url']
    
  data =  urllib.urlencode({'data' : json.dumps(args['data'])})
  print 'Posting %s to %s...' % (data, url)
  
  response = requests.post(url, data=data)
  print response.status_code
  print response.text
  
if __name__ == '__main__':
  sys.exit(main())
