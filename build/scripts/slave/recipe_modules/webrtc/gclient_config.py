# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.gclient import CONFIG_CTX
from slave.recipe_modules.gclient.config import ChromeSvnSubURL,\
  ChromiumSvnSubURL


@CONFIG_CTX(includes=['_webrtc', '_webrtc_limited'])
def webrtc(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def webrtc_clang(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def webrtc_asan(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def webrtc_lsan(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def webrtc_tsan2(c):
  pass


@CONFIG_CTX(includes=['webrtc', 'android'])
def webrtc_android(c):
  pass


@CONFIG_CTX(includes=['webrtc_android'])
def webrtc_android_clang(c):
  pass


@CONFIG_CTX(includes=['chromium', 'android', '_webrtc_limited',
                      '_webrtc_deps', '_webrtc_tot_in_chromium'])
def webrtc_android_apk(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def webrtc_ios(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def valgrind(c):
  """Add Valgrind binaries dependency for WebRTC.

  Since WebRTC DEPS is using relative paths, it it not possible to use a generic
  valgrind config in the gclient recipe module.
  """
  c.solutions[0].custom_deps['third_party/valgrind'] = \
      ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party', 'valgrind',
                        'binaries')


@CONFIG_CTX(includes=['webrtc'])
def tsan_win(c):
  """Add TSan Windows binaries dependency for WebRTC.

  Since WebRTC DEPS is using relative paths, it it not possible to use a generic
  tsan config in the gclient recipe module.
  """
  c.solutions[0].custom_deps['third_party/tsan'] = \
      ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party', 'tsan')


@CONFIG_CTX(includes=['chromium', '_webrtc_deps'])
def chromium_webrtc(c):
  pass


@CONFIG_CTX(includes=['chromium', '_webrtc_deps', '_webrtc_tot_in_chromium'])
def chromium_webrtc_tot(c):
  pass


@CONFIG_CTX()
def _webrtc(c):
  """Add the main solution for WebRTC standalone builds.

  This needs to be in it's own configuration that is added first in the
  dependency chain. Otherwise the webrtc-limited solution will end up as the
  first solution in the gclient spec, which doesn't work.
  """
  s = c.solutions.add()
  s.name = 'src'
  s.url = WebRTCSvnURL(c, 'trunk')
  s.deps_file = 'DEPS'
  s.custom_vars['root_dir'] = 'src'
  c.got_revision_mapping['src'] = 'got_revision'


@CONFIG_CTX()
def _webrtc_deps(c):
  """Add webrtc.DEPS solution for test resources and tools.

  The webrtc.DEPS solution pulls in additional resources needed for running
  WebRTC-specific test setups in Chromium.
  """
  s = c.solutions.add()
  s.name = 'webrtc.DEPS'
  s.url = ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party',
                            'webrtc', 'webrtc.DEPS')
  s.deps_file = 'DEPS'


# Needs to depend on 'chromium' in order to pass recipe_configs_test.py.
@CONFIG_CTX(includes=['chromium'])
def _webrtc_tot_in_chromium(c):
  """Configures src/third_party/webrtc to be the revision decider.

  WebRTC's Android APK tests are built from a Chromium checkout with
  src/third_party/webrtc replaced with ToT instead of the DEPS-pinned revision.
  There are also similar Chromium builders and testers used to catch pre-roll
  test failures for new WebRTC revisions.
  """
  # Have the WebRTC revision appear in the web UI instead of Chromium's.
  del c.got_revision_mapping['src']
  c.got_revision_mapping['src/third_party/webrtc'] = 'got_revision'
  # Needed to get the testers to properly sync the right revision.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'


@CONFIG_CTX()
def _webrtc_limited(c):
  """Helper config for loading the webrtc-limited solution.

  The webrtc-limited solution contains non-redistributable code.
  """
  s = c.solutions.add()
  s.name = 'webrtc-limited'
  s.url = ChromeSvnSubURL(c, 'chrome-internal', 'trunk', 'webrtc-limited')
  s.deps_file = 'DEPS'
  s.custom_vars['root_dir'] = 'src'


def WebRTCSvnURL(c, *pieces):
  BASES = ('http://webrtc.googlecode.com/svn',
           'svn://svn-mirror.golo.chromium.org/webrtc')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)
