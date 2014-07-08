#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Contains configuration and setup of a build scan database.

The databse is a versioned JSON file built of NamedTuples.
"""

import collections
import json
import logging
import optparse
import os
import sys

from common import chromium_utils
from slave import gatekeeper_ng_config


DATA_DIR = os.path.dirname(os.path.abspath(__file__))


# Bump each time there is an incompatible change in build_db.
BUILD_DB_VERSION = 2


_BuildDB = collections.namedtuple('BuildDB', [
    'build_db_version',  # An int representing the build_db version.
    'masters',  # {mastername: {buildername: {buildnumber: BuildDBBuild}}}}
    'sections',  # {section_hash: human_readable_json_of_gatekeeper_section}
])


_BuildDBBuild = collections.namedtuple('BuildDBBuild', [
    'finished',  # True if the build has finished, False otherwise.
    'triggered',  # {section: [steps which triggered the section]}
])


class JsonNode(object):
  """Allows for serialization of NamedTuples to JSON."""
  def _asdict(self):  # pylint: disable=R0201
    return {}

  # TODO(stip): recursively encode child nodes.
  def asJson(self):
    nodes_to_encode = [(k, v) for k, v in self._asdict().iteritems()
                       if hasattr(v, 'asJson')]
    standard_nodes = [(k, v) for k, v in self._asdict().iteritems()
                      if not hasattr(v, 'asJson')]
    newly_encoded_nodes = [(k, v.asJson()) for k, v in nodes_to_encode]

    return dict(standard_nodes + newly_encoded_nodes)


class BuildDB(_BuildDB, JsonNode):
  pass


class BuildDBBuild(_BuildDBBuild, JsonNode):
  pass


class BadConf(Exception):
  pass


def gen_db(**kwargs):
  """Helper function to generate a default database."""
  defaults = [('build_db_version', BUILD_DB_VERSION),
              ('masters', {}),
              ('sections', {})]

  for key, default in defaults:
    kwargs.setdefault(key, default)

  return BuildDB(**kwargs)

def gen_build(**kwargs):
  """Helper function to generate a default build."""
  defaults = [('finished', False),
              ('triggered', {})]

  for key, default in defaults:
    kwargs.setdefault(key, default)

  return BuildDBBuild(**kwargs)


def load_from_json(f):
  """Load a build from a JSON stream."""
  build_db = gen_db()

  json_build_db = json.load(f)

  if json_build_db.get('build_db_version') != BUILD_DB_VERSION:
    raise BadConf('file is an older db version: %r (expecting %d)' % (
        json_build_db.get('build_db_version'), BUILD_DB_VERSION))

  masters = json_build_db.get('masters', {})
  # Convert build dicts into BuildDBBuilds.
  build_db = gen_db()
  for mastername, master in masters.iteritems():
    build_db.masters.setdefault(mastername, {})
    for buildername, builder in master.iteritems():
      build_db.masters[mastername].setdefault(buildername, {})
      for buildnumber, build in builder.iteritems():
        # Note that buildnumber is forced to be an int here, and
        # we use * instead of ** -- until the serializer is recursive,
        # BuildDBBuild will be written as a value list (tuple).
        build_db.masters[mastername][buildername][
            int(buildnumber)] = BuildDBBuild(*build)

  return build_db


def get_build_db(filename):
  """Open the build_db file.

  filename: the filename of the build db.
  """
  build_db = gen_db()

  if os.path.isfile(filename):
    print 'loading build_db from', filename
    try:
      with open(filename) as f:
        build_db = load_from_json(f)
    except BadConf as e:
      new_fn = '%s.old' % filename
      logging.warn('error loading %s: %s, moving to %s' % (
          filename, e, new_fn))
      chromium_utils.MoveFile(filename, new_fn)

  return build_db


def convert_db_to_json(build_db_data, gatekeeper_config, f):
  """Converts build_db to a format suitable for JSON encoding and writes it."""
  # Remove all but the last finished build.
  for builders in build_db_data.masters.values():
    for builder in builders:
      unfinished = [(k, v) for k, v in builders[builder].iteritems()
                    if not v.finished]

      finished = [(k, v) for k, v in builders[builder].iteritems()
                  if v.finished]

      builders[builder] = dict(unfinished)

      if finished:
        max_finished = max(finished, key=lambda x: x[0])
        builders[builder][max_finished[0]] = max_finished[1]


  build_db = gen_db(masters=build_db_data.masters)

  # Output the gatekeeper sections we're operating with, so a human reading the
  # file can debug issues. This is discarded by the parser in get_build_db.
  used_sections = set([])
  for masters in build_db_data.masters.values():
    for builder in masters.values():
      used_sections |= set(t for b in builder.values() for t in b.triggered)

  for master in gatekeeper_config.values():
    for section in master:
      section_hash = gatekeeper_ng_config.gatekeeper_section_hash(section)
      if section_hash in used_sections:
        build_db.sections[section_hash] = section

  json.dump(build_db.asJson(), f, cls=gatekeeper_ng_config.SetEncoder,
            sort_keys=True)


def save_build_db(build_db_data, gatekeeper_config, filename):
  """Save the build_db file.

  build_db: dictionary to jsonize and store as build_db.
  gatekeeper_config: the gatekeeper config used for this pass.
  filename: the filename of the build db.
  """
  print 'saving build_db to', filename
  with open(filename, 'wb') as f:
    convert_db_to_json(build_db_data, gatekeeper_config, f)


def main():
  prog_desc = 'Parses the build_db and outputs to stdout.'
  usage = '%prog [options]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--json', default=os.path.join(DATA_DIR, 'gatekeeper.json'),
                    help='location of gatekeeper configuration file')
  parser.add_option('--build-db', default='build_db.json',
                    help='records the build status information for builders')
  options, _ = parser.parse_args()

  build_db = get_build_db(options.build_db)
  gatekeeper_config = gatekeeper_ng_config.load_gatekeeper_config(options.json)

  convert_db_to_json(build_db, gatekeeper_config, sys.stdout)
  print

  return 0


if __name__ == '__main__':
  sys.exit(main())
