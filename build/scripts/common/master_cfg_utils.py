#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Routines to list, select, and load masters and builders in master.cfg.

These routines help to load up master.cfgs in all directories, then locate
masters and builders among those loaded. This is intended to simplify  master
selection and processing in frontend and build analysis tools, especially the
buildrunner.

When run standalone, the script acts as example usage which lists masters
and builders of a selected master.
"""

# pylint: disable=C0323

import contextlib
import os
import optparse
import sys
import traceback

BASE_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))

sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from common import chromium_utils

# this is required for master.cfg to be loaded properly, since setuptools
# is only required by runbuild.py at the moment.
chromium_utils.AddThirdPartyLibToPath('setuptools-0.6c11')


@contextlib.contextmanager
def TemporaryMasterPasswords():
  all_paths = [os.path.join(BASE_DIR, 'site_config', '.bot_password')]
  all_paths.extend(os.path.join(path, '.apply_issue_password')
                   for path in chromium_utils.ListMasters())
  created_paths = []
  for path in all_paths:
    if not os.path.exists(path):
      try:
        with open(path, 'w') as f:
          f.write('reindeer flotilla\n')
        created_paths.append(path)
      except OSError:
        pass
  try:
    yield
  finally:
    for path in created_paths:
      try:
        os.remove(path)
      except OSError:
        print 'WARNING: Could not remove %s!' % path


def ExecuteConfig(canonical_config):
  """Execute a master.cfg file and return its dictionary.

  WARNING: executing a master.cfg loads modules into the python process.
  Attempting to load another master.cfg with similar module names will
  cause subtle (and not-so-subtle) errors. It is recommended to only call
  this once per process.
  """
  localDict = {'basedir': os.path.dirname(canonical_config),
               '__file__': canonical_config}

  f = open(canonical_config, 'r')

  mycwd = os.getcwd()
  os.chdir(localDict['basedir'])
  beforepath = list(sys.path)  # make a 'backup' of it
  sys.path.append(localDict['basedir'])
  try:
    exec f in localDict
    return localDict
  finally:
    sys.path = beforepath
    os.chdir(mycwd)
    f.close()


def LoadConfig(basedir, config_file='master.cfg', suppress=False):
  """Load and execute a master.cfg file from a directory.

  This is a nicer wrapper around ExecuteConfig which will trap IO or execution
  errors and provide an informative message if one occurs.

  WARNING: executing a master.cfg loads modules into the python process.
  Attempting to load another master.cfg with similar module names will
  cause subtle (and not-so-subtle) errors. It is recommended to only call
  this once per process.
  """

  canonical_basedir = os.path.abspath(os.path.expanduser(basedir))
  canonical_config = os.path.join(canonical_basedir, config_file)

  with TemporaryMasterPasswords():
    try:
      localdict = ExecuteConfig(canonical_config)
    except IOError as err:
      errno, strerror = err
      filename = err.filename
      print >>sys.stderr, 'error %d executing %s: %s: %s' % (errno,
          canonical_config, strerror, filename)
      print >>sys.stderr, traceback.format_exc()
      return None
    except Exception:
      if not suppress:
        print >>sys.stderr, ('error while parsing %s: ' % canonical_config)
        print >>sys.stderr, traceback.format_exc()
      return None

  return localdict


def PrettyPrintInternal(items, columns, title, notfound, spacing=4):
  """Display column-based information from an array of hashes."""
  if not items:
    print
    print notfound
    return

  itemdata = {}
  for col in columns:
    itemdata[col] = [s[col] if col in s else 'n/a' for s in items]

  lengths = {}
  for col in columns:
    datalen = max([len(x) for x in itemdata[col]])
    lengths[col] = max(len(col), datalen)

  maxwidth = sum([lengths[col] for col in columns]) + (
      spacing * (len(columns) - 1))

  spac = ' ' * spacing

  print
  print title
  print
  print spac.join([col.rjust(lengths[col]) for col in columns])
  print '-' * maxwidth

  for i in range(len(items)):
    print spac.join([itemdata[col][i].rjust(lengths[col]) for col in columns])


def PrettyPrintBuilders(builders, master):
  """Pretty-print a list of builders from a master."""

  columns = ['name', 'slavename', 'category']
  title = 'outputting builders for: %s' % master
  notfound = 'no builders found.'
  builders = Denormalize(builders, 'slavenames', 'slavename', columns)
  PrettyPrintInternal(builders, columns, title, notfound)


def PrettyPrintMasters(masterpairs):
  masters = []
  for mastername, path in masterpairs:
    abspath = os.path.abspath(path)
    relpath = os.path.relpath(path)
    shortpath = abspath if len(abspath) < len(relpath) else relpath
    master = {}
    master['mastername'] = mastername
    master['path'] = shortpath
    masters.append(master)

  columns = ['mastername', 'path']
  title = 'listing available masters:'
  notfound = 'no masters found.'
  PrettyPrintInternal(masters, columns, title, notfound)


def Denormalize(items, over, newcol, wanted):
  """Splits a one-to-many hash into many one-to-ones.

  PrettyPrintInternal needs a list of many builders with one slave, this will
  properly format the data as such.

  items: a list of dictionaries to be denormalized
  over: the column (key) over which to separate items
  newcol: the new name of 'over' in the new item
  wanted: the desired keys in the new item

  Example: take some diners with different meals:
    [{'name': 'diner1', 'toasts': ['rye', 'wheat'], eggs:['scrambled']},
     {'name': 'diner2', 'toasts': ['rye', 'white'], eggs:['fried']}]

  Let's say you only cared about your diner/toast options. If you denormalized
  with over=toasts, newcol=toast, wanted=['name', toast'], you'd get:
    [{'name': 'diner1', 'toast': 'rye'},
     {'name': 'diner1', 'toast': 'wheat'},
     {'name': 'diner2', 'toast': 'rye'},
     {'name': 'diner2', 'toast': 'white'}]

  """
  def arrayify(possible_array):
    """Convert 'string' into ['string']. Leave actual arrays alone."""
    if isinstance(possible_array, basestring):
      return [possible_array]
    return possible_array

  wanted_cols = set(wanted)
  wanted_cols.discard(newcol)

  result = []
  for row in items:
    for element in arrayify(row[over]):
      newitem = {}

      # Only bring over the requested columns, instead of all.
      for col in wanted_cols:
        if col in row:
          newitem[col] = row[col]
      newitem[newcol] = element
      result.append(newitem)
  return result


def OnlyGetOne(seq, key, source):
  """Confirm a sequence only contains one unique value and return it.

  This is used when searching for a specific builder. If a match turns up
  multiple results that all share the same builder, then select that builder.
  """

  def uniquify(seq):
    return list(frozenset(seq))
  res = uniquify([s[key] for s in seq])

  if len(res) > 1:
    print >>sys.stderr, 'error: %s too many %ss:' % (source, key)
    for r in res:
      print '  ', r
    return None
  elif not res:
    print 'error: %s zero %ss' % (source, key)
    return None
  else:
    return res[0]


def GetMasters(include_public=True, include_internal=True):
  """Return a pair of (mastername, path) for all masters found."""

  # note: ListMasters uses master.cfg hardcoded as part of its search path
  def parse_master_name(masterpath):
    """Returns a mastername from a pathname to a master."""
    _, tail = os.path.split(masterpath)
    sep = '.'
    hdr = 'master'
    chunks = tail.split(sep)
    if not chunks or chunks[0] != hdr or len(chunks) < 2:
      raise ValueError('unable to parse mastername from path! (%s)' % tail)
    return sep.join(chunks[1:])

  return [(parse_master_name(m), m) for m in
          chromium_utils.ListMasters(include_public=include_public,
                                     include_internal=include_internal)]


def ChooseMaster(searchname):
  """Given a string, find all masters and pick the master that matches."""
  masters = GetMasters()
  masternames = []
  master_lookup = {}
  for mn, path in masters:
    master = {}
    master['mastername'] = mn
    master_lookup[mn] = path
    masternames.append(master)

  candidates = [mn for mn in masternames if mn['mastername'] == searchname]

  errstring = 'string \'%s\' matches' % searchname
  master = OnlyGetOne(candidates, 'mastername', errstring)
  if not master:
    return None

  return master_lookup[master]


def SearchBuilders(builders, spec):
  """Return a list of builders which match what is specified in 'spec'.

  'spec' can be a hash with a key of either 'name', 'slavename', or 'either'.
  This allows for flexibility in how a frontend gets information from the user.
  """
  if 'builder' in spec:
    return [b for b in builders if b['name'] ==
            spec['builder']]
  elif 'hostname' in spec:
    return [b for b in builders if b['slavename']
            == spec['hostname']]
  else:
    return [b for b in builders if (b['name'] ==
            spec['either']) or (b['slavename'] == spec['either'])]


def GetBuilderName(builders, keyval):
  """Return unique builder name from a list of builders."""
  errstring = 'string \'%s\' matches' % keyval
  return OnlyGetOne(builders, 'name', errstring)


def ChooseBuilder(builders, spec):
  """Search through builders matching 'spec' and return it."""

  denormedbuilders = Denormalize(builders, 'slavenames', 'slavename', ['name'])
  candidates = SearchBuilders(denormedbuilders, spec)
  buildername = GetBuilderName(candidates, spec.values()[0])

  if not buildername:
    return None

  builder = [b for b in builders if b['name'] == buildername][0]
  if 'hostname' in spec:
    builder['slavename'] = spec['hostname']
  elif 'either' in spec and spec['either'] in builder['slavenames']:
    builder['slavename'] = spec['either']
  else:
    # User selected builder instead of slavename, so just pick the first
    # slave the builder has.
    builder['slavename'] = builder['slavenames'][0]

  return builder


def main():
  prog_desc = 'List all masters or builders within a master.'
  usage = '%prog [master] [builder or slave]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  (_, args) = parser.parse_args()

  if len(args) > 2:
    parser.error("Too many arguments specified!")

  masterpairs = GetMasters()

  if len(args) < 1:
    PrettyPrintMasters(masterpairs)
    return 0

  master_path = ChooseMaster(args[0])
  if not master_path:
    return 2

  config = LoadConfig(master_path)
  if not config:
    return 2

  mastername = config['BuildmasterConfig']['properties']['mastername']
  builders = config['BuildmasterConfig']['builders']
  if len(args) < 2:
    PrettyPrintBuilders(builders, mastername)
    return 0

  my_builder = ChooseBuilder(builders, {'either': args[1]})

  if not my_builder:
    return 2
  print "Matched %s/%s." % (mastername, my_builder['name'])

  return 0


if __name__ == '__main__':
  sys.exit(main())
