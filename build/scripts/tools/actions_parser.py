#!/usr/bin/env python2.7
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Parses BuildBot `actions.log' and extracts events.

These events can be uploaded as JSON to monitoring endpoints.
"""


import argparse
import collections
import datetime
import glob
import httplib
import json
import logging
import os
import pprint
import re
import sys

import requests


class PostFailedError(RuntimeError):
  pass


# Holds information for a master that will be operated on.
_Master = collections.namedtuple('Master',
    ('name', 'path')
)

class Master(_Master):
  """Class that encapsulates a Master, its data, and operations."""
  # Disable "Class has no '__init__' warning" | pylint: disable=W0232

  # Example action line:
  # **  Fri Aug 22 18:30:50 PDT 2014        make stop
  ACTIONS_RE = re.compile(r'\*\*\s+(.+?)\t(\w.+)')
  # The format to use for the timestamp file.
  TIMESTAMP_FORMAT = '%Y-%m-%d-%H-%M-%S'

  @property
  def actions_log_path(self):
    """Returns: the path to this Master's 'actions.log' file."""
    return os.path.join(self.path, 'actions.log')

  @property
  def timestamp_path(self):
    """Returns: the path to this Master's timestamp file."""
    return os.path.join(self.path, 'actions_parser.timestamp')

  @classmethod
  def fromdir(cls, d):
    """Instantiates a new Master given its base directory."""
    name = os.path.split(d)[1]
    if name.startswith('master.'):
      name = name[7:]
    return cls(
        name=name,
        path=d,
    )

  def get_timestamp(self):
    """Returns the timestamp for this master, or None if there is no timestamp.
    """
    try:
      with open(self.timestamp_path, 'r') as fd:
        timestamp = fd.read()
    except IOError:
      logging.debug("Failed to open difference file for '%s' at: %s",
          self.name, self.timestamp_path)
      return None

    try:
      return datetime.datetime.strptime(timestamp, self.TIMESTAMP_FORMAT)
    except ValueError as e:
      logging.warning("Failed to load timestamp from '%s': %s",
          timestamp, e.message)

  def write_timestamp(self, dt):
    """Writes a new timestamp file for this master with the value 'dt'."""
    value = dt.strftime(self.TIMESTAMP_FORMAT)
    logging.info("Writing timestamp for '%s' at '%s' to: %s",
        self.name, dt, self.timestamp_path)
    with open(self.timestamp_path, 'w') as fd:
      fd.write(value)

  def delete_timestamp(self):
    """Deletes the timestamp file for this master, if it exists."""
    logging.debug("Removing timestamp file for '%s' at: %s",
        self.name, self.timestamp_path)
    try:
      os.remove(self.timestamp_path)
    except Exception as e:
      # Failure to remove is not a fatal error. If the file doesn't exist, it's
      # not even an error.
      logging.debug("Failed to remove timestamp at [%s]: %s",
          self.timestamp_path, e.message)

  def load_actions(self, threshold=None):
    """Loads the set of actions from this master.

    Args:
      threshold: (datetime) if not None, only returns actions with timestamps
          after this time.
    """
    if not os.path.exists(self.actions_log_path):
      logging.warning("No 'actions.log' found for master %s at: %s",
          self.name, self.actions_log_path)

    # Load matches from the 'actions.log'.
    matches = []
    with open(self.actions_log_path, 'r') as fd:
      for line in fd:
        match = self.ACTIONS_RE.match(line)
        if match:
          matches.append(match)

    # Parse the matches into actions
    actions = []
    timestamps = []
    for match in matches:
      datestr, action = match.groups()
      try:
        date = datetime.datetime.strptime(datestr, '%a %b %d %H:%M:%S %Z %Y')
      except ValueError as e:
        logging.error("Failed to parse date from '%s': %s", datestr, e.message)
        continue

      if threshold and date <= threshold:
        logging.debug("Skipping action '%s' from '%s' at %s (below threshold)",
            action, self.name, date)
        continue

      # Parse action
      action = action.strip()
      actions.append((date, action))
      timestamps.append(date)

    # Calculate the largest timestamp (None if there were none)
    last_timestamp = (None) if not timestamps else (max(timestamps))
    return actions, last_timestamp


def do_post(actions, endpoint):
  """Transcribes 'actions' into a JSON dictionary and POSTs it to an endpoint.

  Args:
    actions: JSON-nable data to POST.
    endpoint: The endpoint URL.
  """
  def json_default(obj):
    if isinstance(obj, datetime.datetime):
      return obj.isoformat()
    raise TypeError("Don't know how to translate '%s' to JSON" % (
        type(obj).__name__,))

  json_actions = json.dumps(actions, default=json_default)

  logging.debug("Posting JSON data to [%s]: %s", endpoint, json_actions)
  r = requests.post(endpoint, data=json_actions, verify=True)
  if r.status_code != httplib.OK:
    logging.error("Failed to POST JSON data to [%s]: %s",
        endpoint, r.status_code)
    raise PostFailedError("Unsuccessful HTTP response (%s)" % (r.status_code,))
  return 0


def get_master(checkout_root, name):
  """Returns a Master instance for 'name', or None if one doesn't exist."""
  # Prepend name with 'master.' if not specified.
  if not name.startswith('master.'):
    name = 'master.%s' % (name,)

  # Identify masters as directories containing 'buildbot.tac' files.
  glob_path = os.path.join(checkout_root, '*', 'masters', name, 'buildbot.tac')
  for candidate in glob.iglob(glob_path):
    return Master.fromdir(os.path.split(candidate)[0])
  return None


def get_all_masters(checkout_root):
  """Identifies all Master instances by probing a checkout root."""
  masters = []

  # Identify masters as directories containing 'buildbot.tac' files.
  glob_path = os.path.join(checkout_root, '*', 'masters', '*', 'buildbot.tac')
  for candidate in glob.iglob(glob_path):
    master = Master.fromdir(os.path.split(candidate)[0])

    # Discard this master if there is no 'actions.log' file.
    if not os.path.exists(master.actions_log_path):
      logging.debug("Discarding master '%s': no 'actions.log' available.",
          master.name)
      continue
    masters.append(master)
  return masters


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', action='count',
      help="Increases logging verbosity. Can be specified multiple times.")
  parser.add_argument('-C', '--checkout-root', action='store', metavar='PATH',
      help="The checkout root to use for 'master' probing.")
  parser.add_argument('-A', '--all', action='store_true',
      help="Include output for all Masters hosted on this system.")
  parser.add_argument('-P', '--post', metavar='ENDPOINT',
      help="Post JSON actions for each master to the specified ENDPOINT.")
  parser.add_argument('-c', '--clear-difference', action='store_true',
      help="Clear any existing difference files.")
  parser.add_argument('-D', '--difference', action='store_true',
      help="Calculate the actions since the 'difference' time. After "
           "successful operation, a new difference file will be written.")
  parser.add_argument('mastername', nargs='*',
      help="The names of masters to extract action information for.")

  args = parser.parse_args()

  log_levels = (logging.WARNING, logging.INFO, logging.DEBUG)
  logging.getLogger().setLevel(log_levels[max(args.verbose, len(log_levels)-1)])

  # Identify the checkout root
  checkout_root = args.checkout_root
  if not checkout_root:
    # Our script is in '<ROOT>/<build>/scripts/tools'; we want <ROOT>.
    checkout_root = os.path.abspath(os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
  checkout_root = os.path.expanduser(checkout_root)
  logging.debug("Using checkout root: %s", checkout_root)

  # Get the list of masters to run against.
  masters = []
  if args.all:
    masters += get_all_masters(checkout_root)

  missing_masters = []
  for name in args.mastername:
    master = get_master(checkout_root, name)
    if not master:
      missing_masters.append(name)
      continue
    masters.append(master)

  if missing_masters:
    logging.error("Unable to locate masters: %s", ', '.join(missing_masters))
    return 1

  logging.debug("Collecting 'actions' information for %d master(s)",
      len(masters))
  if logging.getLogger().isEnabledFor(logging.DEBUG):
    for master in masters:
      logging.debug("  - %s", master.name)

  # Construct our actions JSON-able dictionary
  actions = {}
  timestamps = {}
  for master in masters:
    if args.clear_difference:
      master.delete_timestamp()
    actions[master.name], timestamps[master.name] = master.load_actions(
        threshold=(None) if not args.difference else (master.get_timestamp()),
    )

  # Post JSON to endpoint, if configured.
  if actions and args.post:
    try:
      do_post(actions, args.post)
    except PostFailedError:
      logging.exception("Failed to POST to endpoint [%s]" % (args.post,))
      return 2
  elif logging.getLogger().isEnabledFor(logging.INFO):
    logging.info("Loaded action set:\n%s", pprint.pformat(actions))

  # Write the difference file. At this point, all operations have been
  # successful.
  if args.difference:
    logging.info("Writing updated timestamp files")
    for master in masters:
      timestamp = timestamps.get(master.name)
      if not timestamp:
        continue
      master.write_timestamp(timestamp)
  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.WARNING)
  return_code = 1
  try:
    return_code = main()
  except Exception:
    logging.exception("Uncaught exception during execution")
  finally:
    sys.exit(return_code)
