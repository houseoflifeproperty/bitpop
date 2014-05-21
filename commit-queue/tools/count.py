#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Count commits by the commit queue."""

import datetime
import json
import logging
import optparse
import os
import re
import sys
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import find_depot_tools  # pylint: disable=W0611
import subprocess2


def log(repo, args):
  """If extra is True, grab one revision before and one after."""
  args = args or []
  out = subprocess2.check_output(
      ['svn', 'log', '--with-all-revprops', '--xml', repo] + args)
  data = {}
  for logentry in ElementTree.XML(out).findall('logentry'):
    date_str = logentry.find('date').text
    date = datetime.datetime(*map(int, re.split('[^\d]', date_str)[:-1]))
    entry = {
        'author': logentry.find('author').text,
        'date': date,
        'msg': logentry.find('msg').text,
        'revprops': {},
        'commit-bot': False,
    }
    revprops = logentry.find('revprops')
    if revprops is not None:
      for revprop in revprops.findall('property'):
        entry['revprops'][revprop.attrib['name']] = revprop.text
        if revprop.attrib['name'] == 'commit-bot':
          entry['commit-bot'] = True
    data[logentry.attrib['revision']] = entry
  return data


def log_dates(repo, start_date, days):
  """Formats dates so 'svn log' does the right thing. Fetches everything in UTC.
  """
  # http://svnbook.red-bean.com/nightly/en/svn-book.html#svn.tour.revs.dates
  if not days:
    end_inclusive = datetime.date.today()
  else:
    end_inclusive = start_date + datetime.timedelta(days=days)
  actual_days = (end_inclusive - start_date).days
  print('Getting data from %s for %s days' % (start_date, actual_days))
  range_str = (
      '{%s 00:00:00 +0000}:{%s 00:00:00 +0000}' % (start_date, end_inclusive))
  data = log(repo, ['-r', range_str])
  # Strip off everything outside the range.
  start_date_time = datetime.datetime(*start_date.timetuple()[:6])
  if data:
    first = sorted(data.keys())[0]
    if data[first]['date'] < start_date_time:
      del data[first]
  # Strip the commit message to save space.
  for item in data.itervalues():
    del item['msg']
  return data


def monday_last_week():
  """Returns Monday in 'date' object."""
  today = datetime.date.today()
  last_week = today - datetime.timedelta(days=7)
  return last_week - datetime.timedelta(days=(last_week.isoweekday() - 1))


class JSONEncoder(json.JSONEncoder):
  def default(self, o):  # pylint: disable=E0202
    if isinstance(o, datetime.datetime):
      return str(o)
    return super(JSONEncoder, self)


def print_aligned(zipped_list):
  max_len = max(len(i[0]) for i in zipped_list)
  for author, count in zipped_list:
    print('%*s: %d' % (max_len, author, count))


def print_data(log_data, stats_only, top):
  # Calculate stats.
  num_commit_bot = len([True for v in log_data.itervalues() if v['commit-bot']])
  num_total_commits = len(log_data)
  pourcent = 0.
  if num_total_commits:
    pourcent = float(num_commit_bot) * 100. / float(num_total_commits)
  users = {}
  for i in log_data.itervalues():
    if i['commit-bot']:
      users.setdefault(i['author'], 0)
      users[i['author']] += 1

  if not stats_only:
    max_author_len = max(len(i['author']) for i in log_data.itervalues())
    for revision in sorted(log_data.keys()):
      entry = log_data[revision]
      commit_bot = ' '
      if entry['commit-bot']:
        commit_bot = 'c'
      print('%s  %s  %s  %*s' % (
        ('r%s' % revision).rjust(6),
        commit_bot,
        entry['date'].strftime('%Y-%m-%d %H:%M UTC'),
        max_author_len,
        entry['author']))
    print('')

  if top:
    top_users = sorted(
        users.iteritems(), key=lambda x: x[1], reverse=True)[:top]
    top_commits = sum(x[1] for x in top_users)
    p_u = 100. * len(top_users) / len(users)
    p_c = 100. * top_commits / num_commit_bot
    print(
        'Top users:      %6d out of %6d total users  %6.2f%%' %
        (len(top_users), len(users), p_u))
    print(
        '  Committed     %6d out of %6d CQ\'ed commits %5.2f%%' %
        (top_commits, num_commit_bot, p_c))
    if not stats_only:
      print_aligned(top_users)

  non_committers = sorted(
        ( (u, c) for u, c in users.iteritems()
          if not u.endswith('@chromium.org')),
        key=lambda x: x[1], reverse=True)
  if non_committers:
    print('')
    n_c_commits = sum(x[1] for x in non_committers)
    p_u = 100. * len(non_committers) / len(users)
    p_c = 100. * n_c_commits / num_commit_bot
    print(
        'Non-committers: %6d out of %6d total users  %6.2f%%' %
        (len(non_committers), len(users), p_u))
    print(
        '  Committed     %6d out of %6d CQ\'ed commits %5.2f%%' %
        (n_c_commits, num_commit_bot, p_c))
    print('')
    print('Top domains')
    domains = {}
    for user, count in non_committers:
      domain = user.split('@', 1)[1]
      domains.setdefault(domain, 0)
      domains[domain] += count
    domains_stats = sorted(
        ((k, v) for k, v in domains.iteritems()),
        key=lambda x: x[1], reverse=True)
    print_aligned(domains_stats)
    if not stats_only:
      print_aligned(non_committers)

  print('')
  print('Total commits:               %6d' % num_total_commits)
  print(
      'Total commits by commit bot: %6d (%6.1f%%)' % (num_commit_bot, pourcent))


def main():
  parser = optparse.OptionParser(
      description=sys.modules['__main__'].__doc__)
  parser.add_option('-v', '--verbose', action='store_true')
  parser.add_option(
    '-r', '--repo', default='http://src.chromium.org/svn/trunk')
  parser.add_option('-s', '--since', action='store')
  parser.add_option('-d', '--days', type=int, default=7)
  parser.add_option('--all', action='store_true', help='Get ALL the revisions!')
  parser.add_option('--dump', help='Dump json in file')
  parser.add_option('--read', help='Read the data from a file')
  parser.add_option('-o', '--stats_only', action='store_true')
  parser.add_option('--top', default=20, type='int')
  options, args = parser.parse_args()
  if args:
    parser.error('Unsupported args: %s' % args)
  logging.basicConfig(
      level=(logging.DEBUG if options.verbose else logging.ERROR))

  # By default, grab stats for last week.
  if not options.since:
    options.since = monday_last_week()
  else:
    options.since = datetime.date(*map(int, re.split('[^\d]', options.since)))

  if options.read:
    if options.dump:
      parser.error('Can\'t use --dump and --read simultaneously')
    log_data = json.load(open(options.read, 'r'))
    for entry in log_data.itervalues():
      # Convert strings like "2012-09-04 01:14:43.785581" to a datetime object.
      entry['date'] = datetime.datetime.strptime(
          entry['date'], '%Y-%m-%d %H:%M:%S.%f')
  else:
    if options.all:
      log_data = log(options.repo, [])
    else:
      log_data = log_dates(options.repo, options.since, options.days)
    if options.dump:
      json.dump(log_data, open(options.dump, 'w'), cls=JSONEncoder)

  print_data(log_data, options.stats_only, options.top)
  return 0


if __name__ == '__main__':
  sys.exit(main())
