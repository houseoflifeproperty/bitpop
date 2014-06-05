#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

from common import chromium_utils

chromium_utils.AddThirdPartyLibToPath('requests_1_2_3')

import requests  # "Unable to import" pylint: disable=F0401


def main():
  parser = argparse.ArgumentParser(
      description='Get a url and print its document.')
  parser.add_argument('url', help='the url to fetch')
  parser.add_argument('--outfile', help='write output to this file')
  args = parser.parse_args()

  r = requests.get(args.url)
  r.raise_for_status()

  if args.outfile:
    with open(args.outfile, 'w') as f:
      f.write(r.text)
  else:
    print r.text


if __name__ == '__main__':
  sys.exit(main())
