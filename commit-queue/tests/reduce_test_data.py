#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Reduce the amount of data in ../test/data/*.json"""

import json
import logging
import optparse
import os
import re
import sys


class Filterer(object):
  def __init__(self):
    self._deleted_builds = {}
    self.max_cached_builds = 10
    self._allowed_builders = ('linux_clang', 'linux', 'linux_touch')

  def reset(self):
    self._deleted_builds = {}

  def reduce_data(self, data):
    """Reduces the amount of data sent from a server to simplify testing and the
    amount of test data stored.
    """
    self.reset()
    for line in data[:]:
      original_url, original_response = line
      # Unpack and filter the response.
      new_url, new_response = self.filter_response(
          original_url, json.loads(original_response))
      if not new_url or new_response is None:
        data.remove(line)
        continue
      # Repack the string.
      line[1] = json.dumps(new_response, separators=(',',':'))
      logging.info('%s length: %d -> %d' % (
          new_url, len(original_response), len(line[1])))
      if len(line[1]) > 20000:
        logging.debug(line[1])
    return data

  def filter_response(self, url, response):
    """Trims a single request.

    |response| must be decoded json. Decoded json will be returned.
    """
    # Builders
    match = re.match('.+/json/builders/(\w+)(|\?filter=1)$', url)
    if match:
      return url, self._filter_builder(match.group(1), response)

    match = re.match('.+/json/builders(|\?filter=1)$', url)
    if match:
      for builder in response.keys():
        value = self._filter_builder(builder, response[builder])
        if value is None:
          del response[builder]
        else:
          response[builder] = value
      return url, response

    # Pending
    match = re.match('.+/json/builders/(\w+)/pendingBuilds(|\?filter=1)$', url)
    if match:
      assert match.group(1) in self._allowed_builders
      return url, self._filter_pending(response)

    # Builds
    match = re.match('.+/json/builders/(\w+)/builds/_all(|\?filter=1)$', url)
    if match:
      builder = match.group(1)
      assert builder in self._allowed_builders, url
      keys = response.keys()
      keys = [int(k) for k in keys if int(k) not in self._deleted(builder)]
      keys = sorted(keys)[:self.max_cached_builds]
      response = dict((k, v) for k, v in response.iteritems() if int(k) in keys)
      return url, response

    match = re.match('.+/json/builders/(\w+)/builds/\?(.+?)(|\&filter=1)$', url)
    if match:
      assert match.group(1) in self._allowed_builders
      # Ignore the query, reconstruct it from what it kept.
      for build in response.keys():
        value = self._filter_build(response[build])
        if value is None:
          del response[build]
        else:
          response[build] = value
      if not response:
        return None, None
      url = '%s?%s' % (
          url.split('?', 1)[0],
          '&'.join('select=%s' % b for b in sorted(response)))
      return url, response

    match = re.match('.+/json/builders/(\w+)/builds/(\d+)(|\?filter=1)$', url)
    if match:
      return url, self._filter_build(response)

    # Slaves
    match = re.match('.+/json/slaves/([^/]+?)(|\?filter=1)$', url)
    if match:
      return url, self._filter_slave(match.group(1), response)

    match = re.match('.+/json/slaves(|\?filter=1)$', url)
    if match:
      for slave in response.keys():
        value = self._filter_slave(slave, response[slave])
        if value is None:
          del response[slave]
        else:
          response[slave] = value
      return url, response

    # Project
    match = re.match('.+/json/project(|\?filter=1)$', url)
    if match:
      return url, response

    assert False, url

  @staticmethod
  def _filter_pending(pending):
    """Trim pendingBuilds."""
    return pending[:2]

  def _filter_builder(self, builder, response):
    """Trims a builder.

    Reduces the number of cached builds.
    """
    # TODO(maruel): Reduce the number of slaves.
    if builder not in self._allowed_builders:
      return None
    builds_kept = response['cachedBuilds'][-self.max_cached_builds:]
    builds_discarded = response['cachedBuilds'][:-self.max_cached_builds]
    assert len(builds_kept) <= self.max_cached_builds
    assert (
        len(builds_kept) + len(builds_discarded) ==
          len(response['cachedBuilds']))
    if builds_discarded:
      assert min(builds_kept) > max(builds_discarded)
    response['cachedBuilds'] = builds_kept
    self._deleted(builder).union(int(b) for b in builds_discarded)
    if response.get('currentBuilds'):
      response['currentBuilds'] = [
          build for build in response['currentBuilds']
          if int(build) not in self._deleted(builder)
      ]
    if response.get('pendingBuilds', 0) > 2:
      response['pendingBuilds'] = 2
    return response

  def _filter_build(self, response):
    """Trims a build."""
    if response['builderName'] not in self._allowed_builders:
      return None
    if int(response['number']) in self._deleted(response['builderName']):
      return None
    # TODO(maruel): Fix StatusJson to not push that much logs data.
    if 'logs' in response:
      del response['logs']
    if response.get('currentStep') and response['currentStep'].get('logs'):
      del response['currentStep']['logs']
    for step in response['steps']:
      if 'logs' in step:
        del step['logs']
    return response

  def _filter_slave(self, _slave, response):
    """Trims a slave."""
    if response.get('builders'):
      for builder in response['builders'].keys():
        if not builder in self._allowed_builders:
          del response['builders'][builder]
      if not response['builders']:
        return None
    if response.get('builderName'):
      if not response['builderName'] in self._allowed_builders:
        return None
    if response.get('runningBuilds'):
      for i, build in enumerate(response['runningBuilds'][:]):
        value = self._filter_build(build)
        if value is None:
          response['runningBuilds'].remove(build)
        else:
          response['runningBuilds'][i] = value
    return response

  def _deleted(self, builder):
    return self._deleted_builds.get(builder, set())


def main():
  parser = optparse.OptionParser(
      description=sys.modules['__main__'].__doc__)
  parser.add_option('-v', '--verbose', action='count', default=0)
  parser.add_option('-d', '--dry-run', action='store_true')
  options, args = parser.parse_args()
  if args:
    parser.error('Unsupported args: %s' % args)
  logging.basicConfig(
      level=[logging.WARNING, logging.INFO, logging.DEBUG][
        min(2, options.verbose)])

  datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
  for filename in os.listdir(datadir):
    if not filename.endswith('.json') or filename.endswith('_expected.json'):
      continue
    filepath = os.path.join(datadir, filename)
    print 'Processing %s'  % filename
    data = json.load(open(filepath))
    data = Filterer().reduce_data(data)
    if not options.dry_run:
      json.dump(data, open(filepath, 'w'), separators=(',',':'))
  return 0


if __name__ == '__main__':
  sys.exit(main())
