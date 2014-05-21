#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for buildbot_json.py."""

import json
import logging
import os
import cStringIO
import StringIO
import sys
import unittest
import urllib

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

import find_depot_tools  # pylint: disable=W0611
from testing_support import auto_stub

# in tests/
import reduce_test_data  # pylint: disable=F0401

# In root
import buildbot_json


class BuildbotJsonTest(auto_stub.TestCase):
  def setUp(self):
    super(BuildbotJsonTest, self).setUp()
    # Default mock.
    self.old_urlopen = self.mock(urllib, 'urlopen', self.mockurlopen)
    self.mock(sys, 'stderr', cStringIO.StringIO())
    self.mock(sys, 'stdout', cStringIO.StringIO())
    self.mock(buildbot_json.time, 'time', lambda: 1325394000.01)
    self.url = 'http://build.chromium.org/p/tryserver.chromium'
    self.datadir = os.path.join(ROOT_DIR, 'data')
    if not os.path.isdir(self.datadir):
      os.mkdir(self.datadir)
    self.test_id = self.id().split('BuildbotJsonTest.', 1)[1]
    self.filepath = os.path.join(self.datadir, self.test_id) + '.json'
    self.queue = []
    self.training = False
    if os.path.isfile(self.filepath):
      self.queue = json.load(open(self.filepath))
      # Auto upgrade old data.
      for i in xrange(len(self.queue)):
        url = self.queue[i][0]
        if not url.endswith('filter=1'):
          if '?' in url:
            url += '&filter=1'
          else:
            url += '?filter=1'
          self.queue[i][0] = url
          logging.warn('Auto-convert to training because missing filter=1.')
          self.training = True
    self.queue_index = 0
    self.reducer = reduce_test_data.Filterer()

  def tearDown(self):
    if not self.has_failed():
      if self.queue_index < len(self.queue):
        self.queue = self.queue[:self.queue_index]
        logging.warning('Auto-convert to training because of queue overflow')
        self.training = True
      if self.training:
        json.dump(self.queue, open(self.filepath, 'w'), separators=(',',':'))
      self.assertEquals(self.queue_index, len(self.queue))
      self.assertOut('stderr', '')
      self.assertOut('stdout', '')
    else:
      if self.training:
        logging.error('Not saving data even if in training mode.')
    super(BuildbotJsonTest, self).tearDown()
    if self.training:
      self.fail(
          'Don\'t worry, it\'s just updating internal files. Please run '
          'again.\n%s' % '\n'.join(q[0] for q in self.queue))

  def assertOut(self, out, expected):
    """Check stderr/stdout and resets it."""
    self.assertEquals(str(expected), str(getattr(sys, out).getvalue()))
    self.mock(sys, out, cStringIO.StringIO())

  def mockurlopen(self, url):
    self.assertTrue(self.queue_index <= len(self.queue))
    if self.queue_index != len(self.queue):
      expected_url, data = self.queue[self.queue_index]
      if url != expected_url:
        logging.warn(
            'Auto-convert to training because %s != %s.' % (url, expected_url))
        self.training = True
        # Delete the remainder of the queue.
        self.queue = self.queue[:self.queue_index]

    if self.queue_index == len(self.queue):
      data = self.old_urlopen(url).read()
      self.training = True

    # Re-filter it.
    try:
      data = json.loads(data)
    except ValueError:
      self.fail('Failed to decode %s' % url)
    expected_url, new_data = self.reducer.filter_response(url, data)
    assert new_data
    new_data_json = json.dumps(new_data, separators=(',',':'))

    if self.queue_index == len(self.queue):
      self.queue.append((url, new_data_json))
    elif new_data != data:
      logging.warn(
          'Auto-convert to training because url %s\n%s != %s.' % (
            url, data, new_data))
      self.queue[self.queue_index] = [url, new_data_json]
      self.training = True
    channel = StringIO.StringIO(new_data_json)
    channel.headers = '<mocked headers>'
    self.queue_index += 1
    return channel

  def testCommands(self):
    # Assert no new command was added, otherwise a test needs to be written.
    expected = [
        'busy',
        'builds',
        'count',
        'current',
        'disconnected',
        'help',
        'idle',
        'interactive',
        'last_failure',
        'pending',
        'run',
    ]
    actual = [i[3:] for i in dir(buildbot_json) if i.startswith('CMD')]
    self.assertEquals(sorted(expected), sorted(actual))
    for i in actual:
      self.assertTrue(hasattr(self, 'testCMD' + i))

  def testCMDbusy(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDbusy(parser, [self.url, '-b', 'linux']))
    filepath = os.path.join(self.datadir, self.test_id) + '_expected.txt'
    if self.training or not os.path.isfile(filepath):
      # pylint: disable=E1101
      json.dump(sys.stdout.getvalue(), open(filepath, 'w'))
    expected = json.load(open(filepath))
    self.assertOut('stdout', expected)

  def testCMDbuilds(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDbuilds(
          parser, [self.url, '-b', 'linux', '-s', 'vm146-m4', '-q']))
    filepath = os.path.join(self.datadir, self.test_id) + '_expected.txt'
    if self.training or not os.path.isfile(filepath):
      # pylint: disable=E1101
      json.dump(sys.stdout.getvalue(), open(filepath, 'w'))
    expected = json.load(open(filepath))
    self.assertOut('stdout', expected)

  def testCMDcount(self):
    self.mock(buildbot_json.time, 'time', lambda: 1348166285.56)
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDcount(
            parser, [self.url, '-b', 'linux', '-o' '360']))
    filepath = os.path.join(self.datadir, self.test_id) + '_expected.txt'
    if self.training or not os.path.isfile(filepath):
      # pylint: disable=E1101
      json.dump(sys.stdout.getvalue(), open(filepath, 'w'))
    expected = json.load(open(filepath))
    self.assertOut('stdout', expected)

  def testCMDdisconnected(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDdisconnected(parser, [self.url]))
    self.assertOut(
        'stdout',
        'vm112-m4\nvm122-m4\nvm124-m4\nvm131-m4\nvm134-m4\nvm139-m4\nvm143-m4\n'
        'vm146-m4\nvm157-m4\nvm162-m4\nvm165-m4\nvm60-m4\nvm62-m4\nvm64-m4\n')

  def testCMDhelp(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(0, buildbot_json.CMDhelp(parser, []))
    # No need to check exact output here.
    # pylint: disable=E1101
    self.assertTrue(
        'show program\'s version number and exit\n' in sys.stdout.getvalue())
    self.mock(sys, 'stdout', cStringIO.StringIO())

  def testCMDidle(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDidle(parser, [self.url, '--builder', 'linux_clang']))
    self.assertOut(
        'stdout', 'Builder linux_clang: vm104-m4, vm113-m4, vm165-m4\n')

  def testCMDinteractive(self):
    self.mock(sys, 'stdin', cStringIO.StringIO('exit()'))
    parser = buildbot_json.gen_parser()
    try:
      # TODO(maruel): Real testing.
      buildbot_json.CMDinteractive(parser, [self.url])
      self.fail()
    except SystemExit:
      pass
    self.assertOut(
        'stderr',
        'Buildbot interactive console for "http://build.chromium.org'
        '/p/tryserver.chromium".\nHint: Start with typing: '
        '\'buildbot.printable_attributes\' or \'print str(buildbot)\' to '
        'explore.\n')
    self.assertOut('stdout', '>>> ')

  def testCMDlast_failure(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDlast_failure(
            parser, [self.url, '-b', 'linux', '--step', 'compile']))
    self.assertOut(
        'stdout',
        '27369 on vm136-m4: blame:jam@chromium.org\n'
        '27367 on vm158-m4: blame:jam@chromium.org\n')

  def testCMDpending(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(0, buildbot_json.CMDpending(parser, [self.url]))
    self.assertOut('stdout',
        "Builder linux_touch: 2\n"
        "  revision: HEAD\n  change:\n    comment: u''\n"
        "    who:     saintlou@google.com\n  revision: HEAD\n  change:\n"
        "    comment: u''\n    who:     saintlou@google.com\n")

  def testCMDcurrent(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(0, buildbot_json.CMDcurrent(parser, [self.url]))
    filepath = os.path.join(self.datadir, self.test_id) + '_expected.txt'
    if self.training or not os.path.isfile(filepath):
      # pylint: disable=E1101
      json.dump(sys.stdout.getvalue(), open(filepath, 'w'))
    expected = json.load(open(filepath))
    self.assertOut('stdout', expected)

  def testCMDrun(self):
    parser = buildbot_json.gen_parser()
    self.assertEquals(
        0,
        buildbot_json.CMDrun(
          parser, [self.url, "print '\\n'.join(buildbot.builders.keys)"]))
    self.assertOut('stdout', 'linux\nlinux_clang\nlinux_touch\n')

  def testCurrentBuilds(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    actual = []
    for builder in b.builders:
      self.assertEquals([], list(builder.current_builds.cached_children))
      i = 0
      last_build = None
      for c in builder.current_builds:
        self.assertEquals(builder, c.builder)
        actual.append(str(c))
        i += 1
        last_build = c
      if i:
        self.assertEquals(last_build.number, builder.builds[-1].number)
      self.assertEquals(i, len(list(builder.current_builds.cached_children)))
      builder.current_builds.discard()
      self.assertEquals([], list(builder.current_builds.cached_children))

    filepath = os.path.join(self.datadir, self.test_id) + '_expected.json'
    if self.training or not os.path.isfile(filepath):
      json.dump(actual, open(filepath, 'w'))
    expected = json.load(open(filepath))
    self.assertEquals(expected, actual)

  def test_builds_reverse(self):
    # Check the 2 last builds from 'linux' using iterall() instead of
    # __iter__(). The test also confirms that the build object itself is not
    # loaded.
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    actual = []
    for b in b.builders['linux'].builds.iterall():
      actual.append(b.number)
      # When using iterall() the Build data is delay loaded:
      assert b._data is None  # pylint: disable=W0212
      if len(actual) == 2:
        break

    filepath = os.path.join(self.datadir, self.test_id) + '_expected.json'
    if self.training or not os.path.isfile(filepath):
      json.dump(actual, open(filepath, 'w'))
    expected = json.load(open(filepath))
    self.assertEquals(expected, actual)

  def test_build_results(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    # builds.data['results'] is not present.
    self.assertEquals(
        buildbot_json.SUCCESS, b.builders['linux_clang'].builds[1638].result)
    self.assertEquals(
        buildbot_json.SUCCESS,
        b.builders['linux_clang'].builds[1638].steps[0].result)

  def test_build_steps_keys(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    build = b.builders['linux_clang'].builds[1638]
    #self.assertEquals([0, 1, 2, 3], build.steps.keys)

    # Grab cached version. There is none.
    actual = [step for step in build.steps.cached_children]
    self.assertEquals([], actual)

    # Force load.
    actual = [step for step in build.steps]
    self.assertEquals(
        [buildbot_json.SUCCESS] * 4, [step.result for step in actual])
    self.assertEquals(
        [True] * 4, [step.simplified_result for step in actual])
    self.assertEquals(4, len(actual))

    # Grab cached version.
    actual = [step for step in build.steps.cached_children]
    self.assertEquals(
        [buildbot_json.SUCCESS] * 4, [step.result for step in actual])
    self.assertEquals(4, len(actual))

  def test_repr(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    self.assertEquals('<Builder key=linux>', repr(b.builders['linux']))
    self.assertEquals("<Builders keys=['linux']>", repr(b.builders))

  def test_refresh(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    self.assertEquals(True, b.refresh())

  def test_build_step_cached_data(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    build = 30157
    self.assertEquals(
        None, b.builders['linux'].current_builds[build].steps[0].cached_data)
    b.builders['linux'].current_builds[build].steps[0].cache()
    self.assertEquals(
        'update_scripts',
        b.builders['linux'].current_builds[build].steps[0].name)
    self.assertEquals(
        ['browser_tests', 'ui_tests'],
        b.builders['linux'].current_builds[build].steps.failed)
    self.assertEquals(
        2,
        b.builders['linux'].current_builds[build].steps[2
          ].cached_data['step_number'])
    b.refresh()
    # cache_keys() does the same thing as cache().
    b.builders['linux'].current_builds[build].steps.cache_keys()

  def test_contains(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    self.assertTrue('linux' in b.builders)
    self.assertEquals(3, len(list(b.builders.cached_children)))
    try:
      # The dereference of an invalid key when keys are cached will throw an
      # exception.
      # pylint: disable=W0104
      b.builders['non_existent']
      self.fail()
    except KeyError:
      pass

  def test_slaves(self):
    b = buildbot_json.Buildbot('http://build.chromium.org/p/tryserver.chromium')
    self.assertEquals(11, len(b.slaves.names))
    self.assertEquals(False, b.slaves['mini34-m4'].connected)

  def test_build_revision(self):
    class Root(object):
      @staticmethod
      def read(_):
        return {'sourceStamp': {'revision': 321}}
    build = buildbot_json.Build(Root(), '123', None)
    self.assertEquals(321, build.revision)

  def test_build_revision_none(self):
    class Root(object):
      @staticmethod
      def read(_):
        return {}
    build = buildbot_json.Build(Root(), '123', None)
    self.assertEquals(None, build.revision)

  def test_build_duration(self):
    class Root(object):
      @staticmethod
      def read(_):
        return {'times': [3, 15]}
    build = buildbot_json.Build(Root(), '123', None)
    self.assertEquals(12, build.duration)
    self.assertEquals(3, build.start_time)
    self.assertEquals(15, build.end_time)

  def test_build_duration_none(self):
    class Root(object):
      @staticmethod
      def read(_):
        return {}
    build = buildbot_json.Build(Root(), '123', None)
    self.assertEquals(None, build.duration)
    self.assertEquals(None, build.start_time)
    self.assertEquals(None, build.end_time)

  def test_build_steps_names(self):
    class Root(object):
      @staticmethod
      def read(url):  # pylint: disable=E0213
        self.assertEquals('123', url)
        return {'steps': [{'name': 'a'}, {'name': 'b'}]}
    build = buildbot_json.Build(Root(), '123', None)
    self.assertEquals(['a', 'b'], build.steps.keys)

  def test_build_step_duration(self):
    class Root(object):
      @staticmethod
      def read(_):
        return {'steps': [{'times': [3, 15], 'isStarted': True}]}
    build = buildbot_json.Build(Root(), '123', None)
    build_step = buildbot_json.BuildStep(buildbot_json.BuildSteps(build), 0)
    self.assertEquals(12, build_step.duration)
    self.assertEquals(True, build_step.is_running)
    self.assertEquals(True, build_step.is_started)
    self.assertEquals(False, build_step.is_finished)

  def test_build_step_duration_none(self):
    class Root(object):
      @staticmethod
      def read(_):
        return {'steps': [{}]}
    build = buildbot_json.Build(Root(), '123', None)
    build_step = buildbot_json.BuildStep(buildbot_json.BuildSteps(build), 0)
    self.assertEquals(None, build_step.duration)


if __name__ == '__main__':
  logging.basicConfig(level=
      [logging.WARN, logging.INFO, logging.DEBUG][min(2, sys.argv.count('-v'))])
  unittest.main()
