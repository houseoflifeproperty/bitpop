#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for GClient source in chromium_commands.py"""

import unittest

import test_env  # pylint: disable=W0611

from slave.chromium_commands import GClient
from slave.chromium_commands import untangle


class TestableGClient(GClient):
  """Derives from GClient so we can stub/mock parts to make testing easier."""
  def __init__(self, stdout=None):
    """Create a fake GClient oject that doesn't need to actually run.

    Args:
      stdout: the output of the gclient command as a string.
    """
    fake_args = {'workdir': 'foo',
            'svnurl': 'bar',
            'gclient_spec': 'baz',
            'env': {}}
    GClient.__init__(self, None, None, fake_args)

    class FakeCommand(object):
      def __init__(self, stdout):
        self.stdout = stdout
    self.command = FakeCommand(stdout)


# The following stdout snippets were captured from real output of the
# Update Step on buildbots.
SVN_CHECKOUT_STDOUT = """solutions=[...]

________ running 'svn checkout http://src.chromium.org/svn/trunk/src \
.../build/src' in '.../build'
 U   .../build/src
Checked out revision 12345.

________ running 'svn checkout http://src.chromium.org/native_client/trunk\
/src/native_client .../build/src/native_client' in '.../build'
 U   .../build/src/native_client/src
Checked out revision 98765.

________ running 'svn checkout svn://svn.chromium.org/webrtc/stable/webrtc@4297\
 .../build/src/third_party/webrtc' in '.../build'
 U   .../build/src/third_party/webrtc
Checked out revision 4297.

________ running 'svn checkout http://svn.webkit.org/repository/webkit/trunk\
@66952 .../build/src/third_party/WebKit --revision 66952' in '.../build'
 U   .../build/src/third_party/WebKit
Checked out revision 67890."""

SVN_UPDATE_STDOUT = """solutions=[...]

________ running 'svn update http://src.chromium.org/svn/trunk/src \
.../build/src' in '.../build'
 U   .../build/src
Updated to revision 12345.

________ running 'svn update http://src.chromium.org/native_client/trunk\
/src/native_client .../build/src/native_client' in '.../build'
 U   .../build/src/native_client/src
Updated to revision 98765.

________ running 'svn update svn://svn.chromium.org/webrtc/stable/webrtc@4297 \
.../build/src/third_party/webrtc' in '.../build'
 U   .../build/src/third_party/webrtc
Updated to revision 4297.

________ running 'svn update http://svn.webkit.org/repository/webkit/trunk\
@66952 .../build/src/third_party/WebKit --revision 66952' in '.../build'
 U   .../build/src/third_party/WebKit
Updated to revision 67890."""

SVN_UPDATE_NO_CHANGE_STDOUT = """solutions=[...]

________ running 'svn update http://src.chromium.org/svn/trunk/src \
.../build/src' in '.../build'
At revision 12345.

________ running 'svn update http://src.chromium.org/native_client/trunk/\
src/native_client .../build/src/native_client' in '.../build'
At revision 98765.

________ running 'svn update svn://svn.chromium.org/webrtc/stable/webrtc@4297 \
.../build/src/third_party/webrtc' in '.../build'
At revision 4297.

________ running 'svn update http://svn.webkit.org/repository/webkit/trunk/\
@66952 .../build/src/third_party/WebKit --revision 66952' in '.../build'
At revision 67890."""

GCLIENT_SYNC_NO_CHANGE_STDOUT = """solutions=[...]

Syncing projects:  0% (0/2)
_____ src at 12345

Syncing projects:  50% (12/24)
_____ src/native_client at 98765

Syncing projects:  60% (14/24)
_____ src/third_party/webrtc at 4297

Syncing projects:  77% (45/58)
_____ src/third_party/WebKit at 67890"""

GCLIENT_SYNC_MULTI_JOB_STDOUT = """solutions=[...]
1>
1>_____ src at 59820
1>
2>_____ src/chrome/test/data/layout_tests/LayoutTests/platform/chromium-win/\
storage/domstorage at 67701
2>
3>_____ src/chrome/test/data/layout_tests/LayoutTests/fast/events at 67701
3>
5>_____ src/chrome/test/data/layout_tests/LayoutTests/fast/workers at 67701
5>
7>_____ src/third_party/ots at 35
7>
6>_____ src/breakpad/src at 692
8>
8>_____ src/third_party/libvpx/lib at 59445
8>
6>
...

"""

# DEPS change webkit version from 69169 to 69168
GCLIENT_SYNC_MULTI_JOB_DEPS_TRY_STDOUT = """
.../build/src/DEPS

________ running 'svn update --revision BASE' in '.../build/src'
Restored 'DEPS'
At revision 61624.

Syncing projects:  76% (46/60)

________ running 'svn update --revision BASE' in '.../build/src/third_party/\
WebKit'
At revision 12345.

Syncing projects: 100% (60/60)
Syncing projects: 100% (60/60), done.

solutions=[{"name":"src","url":"http://src.chromium.org/svn/trunk/src"\
,"custom_deps":{"src/webkit/data/layout_tests/LayoutTests":None,\
"src/third_party/WebKit/LayoutTests":None,},"custom_vars":{"webkit_trunk"\
:"http://svn.webkit.org/repository/webkit/trunk","googlecode_url":\
"http://%s.googlecode.com/svn",},},]
1>
1>_____ src at 61624
1>
2>
2>________ running 'svn update .../build/src/chrome/test/data/layout_tests/\
LayoutTests/platform/chromium-win/storage/domstorage --revision 69169' \
in '.../build'
3>
3>________ running 'svn update .../build/src/chrome/test/data/layout_tests/\
LayoutTests/fast/events --revision 69169' in '.../build'
2>
3>
2>At revision 69169.
2>
3>At revision 69169.
3>

51>
51>________ running 'svn update .../build/src/third_party/WebKit/ \
--revision 69169' in '.../build'
51>
51>At revision 69169.
51>

________ running '/usr/bin/python src/build/gyp_chromium' in '.../build'
Updating projects from gyp files...
Generating .../build/src/sandbox/sandbox.Makefile

patching file DEPS

solutions=[{"name":"src","url":"http://src.chromium.org/svn/trunk/src"\
,"custom_deps":{"src/webkit/data/layout_tests/LayoutTests":None,\
"src/third_party/WebKit/LayoutTests":None,},"custom_vars":{"webkit_trunk":\
"http://svn.webkit.org/repository/webkit/trunk","googlecode_url":\
"http://%s.googlecode.com/svn",},},]
1>
1>_____ src at 61624
1>
2>
2>________ running 'svn update .../build/src/chrome/test/data/layout_tests/\
LayoutTests/platform/chromium-win/storage/domstorage --revision 69168' \
in '.../build'
3>
3>________ running 'svn update .../build/src/chrome/test/data/layout_tests/\
LayoutTests/fast/events --revision 69168' in '.../build'
2>
3>
3>At revision 69168.
3>
2>At revision 69168.
2>

47>
47>________ running 'svn update .../build/src/third_party/WebKit \
--revision 69168' in '.../build'
47>At revision 69168.
47>

________ running '/usr/bin/python src/build/gyp_chromium' in '.../build'
Updating projects from gyp files...
Generating .../build/src/sandbox/sandbox.Makefile
"""

NACL_CHECKOUT = """
solutions=[{"name":"native_client","url":"http://src.chromium.org/native_clie...
1>________ running 'svn update /build/native_client --revision 11' in '/build'
1>U    /build.sh
1>Updated to revision 11.
3>________ running 'svn update /build/native_client/tools/perf_expectations \
--revision 191009' in '/build'
4>________ running 'svn update /build/testing/gtest --revision 629' in '/build'
2>________ running 'svn update /build/breakpad/src --revision 1172' in '/build'
3>At revision 191009.
2>At revision 1172.
4>At revision 629.
"""


class GClientSourceTest(unittest.TestCase):

  def testParseGotRevision_NoRevisions(self):
    gclient = TestableGClient("hello world!")
    actual = gclient.parseGotRevision()
    expected = {}
    self.assertEqual(expected, actual)

  def testParseGotRevision_Checkout(self):
    gclient = TestableGClient(SVN_CHECKOUT_STDOUT)
    actual = gclient.parseGotRevision()
    expected = {
      'got_chromium_revision': '12345',
      'got_nacl_revision': '98765',
      'got_revision': '12345',
      'got_webkit_revision': '67890',
      'got_webrtc_revision': '4297',
    }
    self.assertEqual(expected, actual)

  def testParseGotRevision_Update(self):
    gclient = TestableGClient(SVN_UPDATE_STDOUT)
    actual = gclient.parseGotRevision()
    expected = {
      'got_chromium_revision': '12345',
      'got_nacl_revision': '98765',
      'got_revision': '12345',
      'got_webkit_revision': '67890',
      'got_webrtc_revision': '4297',
    }
    self.assertEqual(expected, actual)

  def testParseGotRevision_UpdateNoChange(self):
    gclient = TestableGClient(SVN_UPDATE_NO_CHANGE_STDOUT)
    actual = gclient.parseGotRevision()
    expected = {
      'got_chromium_revision': '12345',
      'got_nacl_revision': '98765',
      'got_revision': '12345',
      'got_webkit_revision': '67890',
      'got_webrtc_revision': '4297',
    }
    self.assertEqual(expected, actual)

  def testParseGotRevision_GClientSyncNoChange(self):
    gclient = TestableGClient(GCLIENT_SYNC_NO_CHANGE_STDOUT)
    actual = gclient.parseGotRevision()
    expected = {
      'got_chromium_revision': '12345',
      'got_nacl_revision': '98765',
      'got_revision': '12345',
      'got_webkit_revision': '67890',
      'got_webrtc_revision': '4297',
    }
    self.assertEqual(expected, actual)

  def testParseGotRevision_MulitJob(self):
    gclient = TestableGClient(stdout=GCLIENT_SYNC_MULTI_JOB_STDOUT)
    actual = gclient.parseGotRevision()
    # The truncated stdout misses some values.
    expected = {
      'got_chromium_revision': '59820',
      'got_revision': '59820',
    }
    self.assertEqual(expected, actual)

  def testParseGotRevision_MultiJobDepsTry(self):
    gclient = TestableGClient(stdout=GCLIENT_SYNC_MULTI_JOB_DEPS_TRY_STDOUT)
    actual = gclient.parseGotRevision()
    expected = {
      # Finds the revision in the changed DEPS, not the first one, e.g. 69168,
      # not 12345.
      'got_chromium_revision': '61624',
      'got_revision': '61624',
      'got_webkit_revision': '69168',
    }
    self.assertEqual(expected, actual)

  def testParseGotRevision_Nacl(self):
    gclient = TestableGClient(stdout=NACL_CHECKOUT)
    actual = gclient.parseGotRevision()
    expected = {
      'got_revision': '11',
    }
    self.assertEqual(expected, actual)

  def testUntangle_UpToDoubleDigits(self):
    stdout_lines = ['4>four', '9>nine', '1>one', '6>six', '3>three',
                    '10>ten', '7>seven', '5>five', '8>eight', '2>two']
    self.assertEqual(['one', 'two', 'three', 'four', 'five',
                      'six', 'seven', 'eight', 'nine', 'ten'],
                     untangle(stdout_lines))

  def testUntangle_MultiplesAndUnMatchingLines(self):
    stdout_lines = ['unmatching (solutions...)',
                    '1>first set, first 1',
                    '2>first set, first 2',
                    '2>first set, second 2',
                    '1>first set, second 1',
                    'unmatching (patching file...)',
                    'unmatching (solutions again...)',
                    '2>second set, first 2',
                    '1>second set, first 1',
                    '1>second set, second 1']
    self.assertEqual(['unmatching (solutions...)',
                      'first set, first 1',
                      'first set, second 1',
                      'first set, first 2',
                      'first set, second 2',
                      'unmatching (patching file...)',
                      'unmatching (solutions again...)',
                      'second set, first 1',
                      'second set, second 1',
                      'second set, first 2'],
                     untangle(stdout_lines))

  def testUntangle_GClientSync(self):
    stdout_lines = GCLIENT_SYNC_MULTI_JOB_STDOUT.splitlines(False)
    self.assertEqual([
        'solutions=[...]',
        '_____ src at 59820',
        '_____ src/chrome/test/data/layout_tests/LayoutTests/'
        'platform/chromium-win/storage/domstorage at 67701',
        '_____ src/chrome/test/data/layout_tests/LayoutTests/'
        'fast/events at 67701',
        '_____ src/chrome/test/data/layout_tests/LayoutTests/'
        'fast/workers at 67701',
        '_____ src/breakpad/src at 692',
        '_____ src/third_party/ots at 35',
        '_____ src/third_party/libvpx/lib at 59445',
        '...'], untangle(stdout_lines))

  def testUntangle_GClientSyncForDepsTrybot(self):
    stdout_lines = GCLIENT_SYNC_MULTI_JOB_DEPS_TRY_STDOUT.splitlines(False)
    self.assertEqual([
        '.../build/src/DEPS',
        '________ running \'svn update --revision BASE\' in \'.../build/src\'',
        'Restored \'DEPS\'',
        'At revision 61624.',
        'Syncing projects:  76% (46/60)',
        '________ running \'svn update --revision BASE\' '
        'in \'.../build/src/third_party/WebKit\'',
        'At revision 12345.',
        'Syncing projects: 100% (60/60)',
        'Syncing projects: 100% (60/60), done.',
        'solutions=[{"name":"src","url":"http://src.chromium.org/svn/'
        'trunk/src","custom_deps":{"src/webkit/data/layout_tests/'
        'LayoutTests":None,"src/third_party/WebKit/LayoutTests":None,},'
        '"custom_vars":{"webkit_trunk":"http://svn.webkit.org/repository/'
        'webkit/trunk","googlecode_url":"http://%s.googlecode.com/svn",},},]',
        '_____ src at 61624',
        '________ running \'svn update .../build/src/chrome/test/data/'
        'layout_tests/LayoutTests/platform/chromium-win/storage/domstorage '
        '--revision 69169\' in \'.../build\'',
        'At revision 69169.',
        '________ running \'svn update .../build/src/chrome/test/data/'
        'layout_tests/LayoutTests/fast/events --revision 69169\' '
        'in \'.../build\'',
        'At revision 69169.',
        '________ running \'svn update .../build/src/third_party/WebKit/'
        ' --revision 69169\' in \'.../build\'',
        'At revision 69169.',
        '________ running \'/usr/bin/python src/build/'
        'gyp_chromium\' in \'.../build\'',
        'Updating projects from gyp files...',
        'Generating .../build/src/sandbox/sandbox.Makefile',
        'patching file DEPS',
        'solutions=[{"name":"src","url":"http://src.chromium.org/svn/'
        'trunk/src","custom_deps":{"src/webkit/data/layout_tests/'
        'LayoutTests":None,"src/third_party/WebKit/LayoutTests":None,},'
        '"custom_vars":{"webkit_trunk":"http://svn.webkit.org/repository/'
        'webkit/trunk","googlecode_url":"http://%s.googlecode.com/svn",},},]',
        '_____ src at 61624',
        '________ running \'svn update .../build/src/chrome/test/data/'
        'layout_tests/LayoutTests/platform/chromium-win/storage/domstorage '
        '--revision 69168\' in \'.../build\'',
        'At revision 69168.',
        '________ running \'svn update .../build/src/chrome/test/data/'
        'layout_tests/LayoutTests/fast/events '
        '--revision 69168\' in \'.../build\'',
        'At revision 69168.',
        '________ running \'svn update .../build/src/third_party/WebKit'
        ' --revision 69168\' in \'.../build\'',
        'At revision 69168.',
        '________ running \'/usr/bin/python src/build/'
        'gyp_chromium\' in \'.../build\'',
        'Updating projects from gyp files...',
        'Generating .../build/src/sandbox/sandbox.Makefile'],
        untangle(stdout_lines))


if __name__ == '__main__':
  unittest.main()
