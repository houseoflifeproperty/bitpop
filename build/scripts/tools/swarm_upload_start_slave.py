#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Upload the start_slave script to the specified swarm server."""

import logging
import optparse
import os
import sys
import urlparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common import url_helper

# The start_slave file to upload.
START_SLAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'swarm_bootstrap', 'start_slave.py')


def main():
  SWARM_SERVER = 'https://chromium-swarm.appspot.com'
  SWARM_SERVER_DEV = 'https://chromium-swarm-dev.appspot.com'

  parser = optparse.OptionParser(usage='%prog [options]',
                                 description=sys.modules[__name__].__doc__)
  parser.add_option('--swarm-server', metavar='HOST',
                    help='The swarm server to update; default: %default',
                    default=SWARM_SERVER_DEV)
  parser.add_option('-p', '--use-prod', action='store_const',
                    help='Shorthand for --swarm_server %s; e.g. the '
                    'production swarm server instead of the development one.' %
                    SWARM_SERVER,
                    dest='swarm_server',
                    const=SWARM_SERVER)
  parser.add_option('-v', '--verbose', action='store_true',
                    help='Set logging level to DEBUG. Optional. Defaults to '
                    'ERROR level.')

  options, args = parser.parse_args()

  if args:
    parser.error('Unknown arguments, %s' % args)

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.ERROR)

  if not os.path.exists(START_SLAVE):
    logging.error('No start slave script found at %s, aborting.', START_SLAVE)
    return 1

  logging.info('Loading start_slave.py')
  with open(START_SLAVE, 'rb') as f:
    start_slave_contents = f.read()

  upload_url = urlparse.urljoin(options.swarm_server,
                                '/upload_start_slave')
  logging.info('Uploading script to %s', upload_url)

  url_helper.upload_files(upload_url, [],
                          [('script', 'script', start_slave_contents)])


if __name__ == '__main__':
  sys.exit(main())
