# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Launches the gatekeeper."""

DEPS = [
  'json',
  'path',
  'python',
]


def gatekeeper_step(api, tree_name, tree_args):
  gatekeeper = api.path['build'].join('scripts', 'slave', 'gatekeeper_ng.py')
  json_file = api.path['build'].join('scripts', 'slave', 'gatekeeper.json')

  args = ['-v', '--json', json_file]

  if tree_args.get('status-url'):
    args.extend(['--status-url', tree_args['status-url']])
  if tree_args.get('set-status'):
    args.append('--set-status')
  if tree_args.get('open-tree'):
    args.append('--open-tree')
  if tree_args.get('track-revisions'):
    args.append('--track-revisions')
  if tree_args.get('revision-properties'):
    args.extend(['--revision-properties', tree_args['revision-properties']])
  if tree_args.get('build-db'):
    args.extend(['--build-db', tree_args['build-db']])
  if tree_args.get('password-file'):
    args.extend(['--password-file', tree_args['password-file']])

  if tree_args.get('masters'):
    args.extend(tree_args['masters'])

  return api.python('gatekeeper: %s' % str(tree_name), gatekeeper, args)


def GenSteps(api):
  step_result = api.json.read(
    'reading gatekeeper_trees.json',
    api.path['build'].join('scripts', 'slave', 'gatekeeper_trees.json'),
    # Needed for training step.
    step_test_data=lambda: api.json.test_api.output({
      'blink': {
        'build-db': 'blink_build_db.json',
        'masters': [
          'https://build.chromium.org/p/chromium.webkit'
          ],
        'open-tree': True,
        'password-file': '.blink_status_password',
        'revision-properties': 'got_revision,got_webkit_revision',
        'set-status': True,
        'status-url': 'https://blink-status.appspot.com',
        'track-revisions': True,
        }
      }
    )
  )
  trees = step_result.json.output
  #TODO(martiniss) convert loop
  for tree_name, tree_args in trees.iteritems():
    gatekeeper_step(api, tree_name, tree_args)

def GenTests(api):
  yield api.test('basic')
