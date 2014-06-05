#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Loads gatekeeper configuration files for use with gatekeeper_ng.py.

The gatekeeper json configuration file has two main sections: 'masters'
and 'categories.' The following shows the breakdown of a possible config,
but note that all nodes are optional (including the root 'masters' and
'categories' nodes).

A builder ultimately needs 4 lists (sets):
  closing_steps: steps which close the tree on failure or omission
  forgiving_steps: steps which close the tree but don't email committers
  tree_notify: any additional emails to notify on tree failure
  sheriff_classes: classes of sheriffs to notify on build failure

Builders can inherit these properties from categories, they can inherit
tree_notify and sheriff_classes from their master, and they can have these
properties assigned in the builder itself. Any property not specified
is considered blank (empty set), and inheritance is always constructive (you
can't remove a property by inheriting or overwriting it). Builders can inherit
categories from their master.

A master consists of zero or more sections, which specify which builders are
watched by the section and what action should be taken. A section can specify
tree_closing to be false, which causes the section to only send out emails
instead of closing the tree. A section or builder can also specify to respect
a build's failure status with respect_build_status.

The 'subject_template' key is the template used for the email subjects. Its
formatting arguments are found at https://chromium.googlesource.com/chromium/
  tools/chromium-build/+/master/gatekeeper_mailer.py, but the list is
reproduced here:

  %(result)s: 'warning' or 'failure'
  %(project_name): 'Chromium', 'Chromium Perf', etc.
  %(builder_name): the builder name
  %(reason): reason for launching the build
  %(revision): build revision
  %(buildnumber): buildnumber

'forgive_all' converts all closing_steps to be forgiving_steps. Since
forgiving_steps only email sheriffs + watchlist (not the committer), this is a
great way to set up experimental or informational builders without spamming
people. It is enabled by providing the string 'true'.

'forgiving_optional' and 'closing_optional' work just like 'forgiving_steps'
and 'closing_steps', but they won't close if the step is missing. This is like
previous gatekeeper behavior. They can be set to '*', which will match all
steps in the builder.

The 'comment' key can be put anywhere and is ignored by the parser.

# Python, not JSON.
{
  'masters': {
    'http://build.chromium.org/p/chromium.win': [
      {
        'sheriff_classes': ['sheriff_win'],
        'tree_notify': ['a_watcher@chromium.org'],
        'categories': ['win_extra'],
        'builders': {
          'XP Tests (1)': {
            'categories': ['win_tests'],
            'closing_steps': ['xp_special_step'],
            'forgiving_steps': ['archive'],
            'tree_notify': ['xp_watchers@chromium.org'],
            'sheriff_classes': ['sheriff_xp'],
          }
        }
      }
    ]
  },
  'categories': {
    'win_tests': {
      'comment': 'this is for all windows testers',
      'closing_steps': ['startup_test'],
      'forgiving_steps': ['boot_windows'],
      'tree_notify': ['win_watchers@chromium.org'],
      'sheriff_classes': ['sheriff_win_test']
    },
    'win_extra': {
      'closing_steps': ['extra_win_step']
      'subject_template': 'windows heads up on %(builder_name)',
    }
  }
}

In this case, XP Tests (1) would be flattened down to:
  closing_steps: ['startup_test', 'win_tests']
  forgiving_steps: ['archive', 'boot_windows']
  tree_notify: ['xp_watchers@chromium.org', 'win_watchers@chromium.org',
                'a_watcher@chromium.org']
  sheriff_classes: ['sheriff_win', 'sheriff_win_test', 'sheriff_xp']

Again, fields are optional and treated as empty lists/sets/strings if not
present.
"""

import copy
import cStringIO
import hashlib
import json
import optparse
import os
import sys


DATA_DIR = os.path.dirname(os.path.abspath(__file__))


# Keys which have defaults besides None or set([]).
DEFAULTS = {
    'subject_template': ('buildbot %(result)s in %(project_name)s on '
                         '%(builder_name)s, revision %(revision)s'),
}


def allowed_keys(test_dict, *keys):
  keys = keys + ('comment',)
  assert all(k in keys for k in test_dict), (
      'not valid: %s; allowed: %s' % (
          ', '.join(set(test_dict.keys()) - set(keys)),
          ', '.join(keys)))


def load_gatekeeper_config(filename):
  """Loads and verifies config json, constructs builder config dict."""

  # Keys which are allowed in a master or builder section.
  master_keys = ['excluded_builders',
                 'excluded_steps',
                 'forgive_all',
                 'sheriff_classes',
                 'subject_template',
                 'tree_notify',
  ]

  builder_keys = ['closing_optional',
                  'closing_steps',
                  'excluded_builders',
                  'excluded_steps',
                  'forgive_all',
                  'forgiving_optional',
                  'forgiving_steps',
                  'sheriff_classes',
                  'subject_template',
                  'tree_notify',
  ]

  # These keys are strings instead of sets. Strings can't be merged,
  # so more specific (master -> category -> builder) strings clobber
  # more generic ones.
  strings = ['forgive_all', 'subject_template']

  with open(filename) as f:
    raw_gatekeeper_config = json.load(f)

  allowed_keys(raw_gatekeeper_config, 'categories', 'masters')

  categories = raw_gatekeeper_config.get('categories', {})
  masters = raw_gatekeeper_config.get('masters', {})

  for category in categories.values():
    allowed_keys(category, *builder_keys)

  gatekeeper_config = {}
  for master_url, master_sections in masters.iteritems():
    for master_section in master_sections:
      gatekeeper_config.setdefault(master_url, []).append({})
      allowed_keys(master_section, 'builders', 'categories', 'close_tree',
                   'respect_build_status', *master_keys)

      builders = master_section.get('builders', {})
      for buildername, builder in builders.iteritems():
        allowed_keys(builder, 'categories', *builder_keys)
        for key, item in builder.iteritems():
          if key in strings:
            assert isinstance(item, basestring)
          else:
            assert isinstance(item, list)
            assert all(isinstance(elem, basestring) for elem in item)

        gatekeeper_config[master_url][-1].setdefault(buildername, {})
        gatekeeper_builder = gatekeeper_config[master_url][-1][buildername]

        # Populate with specified defaults.
        for k in builder_keys:
          if k in DEFAULTS:
            gatekeeper_builder.setdefault(k, DEFAULTS[k])
          elif k in strings:
            gatekeeper_builder.setdefault(k, '')
          else:
            gatekeeper_builder.setdefault(k, set())

        # Inherit any values from the master.
        for k in master_keys:
          if k in strings:
            if k in master_section:
              gatekeeper_builder[k] = master_section[k]
          else:
            gatekeeper_builder[k] |= set(master_section.get(k, []))

        gatekeeper_builder['close_tree'] = master_section.get('close_tree',
                                                              True)
        gatekeeper_builder['respect_build_status'] = master_section.get(
            'respect_build_status', False)

        # Inherit any values from the categories.
        all_categories = (builder.get('categories', []) +
                          master_section.get( 'categories', []))
        for c in all_categories:
          for k in builder_keys:
            if k in strings:
              if k in categories[c]:
                gatekeeper_builder[k] = categories[c][k]
            else:
              gatekeeper_builder[k] |= set(categories[c].get(k, []))

        # Add in any builder-specific values.
        for k in builder_keys:
          if k in strings:
            if k in builder:
              gatekeeper_builder[k] = builder[k]
          else:
            gatekeeper_builder[k] |= set(builder.get(k, []))

        # Builder postprocessing.
        if gatekeeper_builder['forgive_all'] == 'true':
          gatekeeper_builder['forgiving_steps'] |= gatekeeper_builder[
              'closing_steps']
          gatekeeper_builder['forgiving_optional'] |= gatekeeper_builder[
              'closing_optional']
          gatekeeper_builder['closing_steps'] = set([])
          gatekeeper_builder['closing_optional'] = set([])

  return gatekeeper_config


def gatekeeper_section_hash(gatekeeper_section):
  st = cStringIO.StringIO()
  flatten_to_json(gatekeeper_section, st)
  return hashlib.sha256(st.getvalue()).hexdigest()


def inject_hashes(gatekeeper_config):
  new_config = copy.deepcopy(gatekeeper_config)
  for master in new_config.values():
    for section in master:
      section['section_hash'] = gatekeeper_section_hash(section)
  return new_config


# Python's sets aren't JSON-encodable, so we convert them to lists here.
class SetEncoder(json.JSONEncoder):
  # pylint: disable=E0202
  def default(self, obj):
    if isinstance(obj, set):
      return sorted(list(obj))
    return json.JSONEncoder.default(self, obj)


def flatten_to_json(gatekeeper_config, stream):
  json.dump(gatekeeper_config, stream, cls=SetEncoder, sort_keys=True)


def main():
  prog_desc = 'Reads gatekeeper.json and emits a flattened config.'
  usage = '%prog [options]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--json', default=os.path.join(DATA_DIR, 'gatekeeper.json'),
                    help='location of gatekeeper configuration file')
  parser.add_option('--no-hashes', action='store_true',
                    help='don\'t insert gatekeeper section hashes')
  options, _ = parser.parse_args()

  gatekeeper_config = load_gatekeeper_config(options.json)

  if not options.no_hashes:
    gatekeeper_config = inject_hashes(gatekeeper_config)

  flatten_to_json(gatekeeper_config, sys.stdout)
  print

  return 0


if __name__ == '__main__':
  sys.exit(main())
